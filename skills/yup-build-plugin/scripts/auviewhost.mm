// Minimal AUv2 Cocoa UI host: instantiates several AUs in one process and opens
// each editor through kAudioUnitProperty_CocoaUI, the way AU Lab / Logic do.
//
// usage: auviewhost [--seconds N] ID [ID ...]
//   ID = type:subtype:manu                              an installed AU
//   ID = path/to/X.component@type:subtype:manu          an uninstalled bundle, registered
//                                                       in-process under that (unused) ID
//
// build: clang++ -std=c++20 -fobjc-arc auviewhost.mm -framework AppKit \
//            -framework AudioToolbox -framework AudioUnit -o auviewhost
//
// Exits non-zero when any editor cannot be created. Watch stderr for the
// Objective-C runtime "Class X is implemented in both" warning.

#import <AppKit/AppKit.h>
#import <AudioToolbox/AudioToolbox.h>
#import <AudioUnit/AUCocoaUIView.h>
#include <dlfcn.h>
#include <cstdio>
#include <string>
#include <vector>

static OSType fourCC (const std::string& s)
{
    return (OSType (s[0]) << 24) | (OSType (s[1]) << 16) | (OSType (s[2]) << 8) | OSType (s[3]);
}

static const char* imageOf (Class cls)
{
    Dl_info info {};
    if (cls != nil && dladdr ((__bridge void*) cls, &info) && info.dli_fname != nullptr)
        return info.dli_fname;
    return "?";
}

int main (int argc, const char** argv)
{
    @autoreleasepool
    {
        double seconds = 3.0;
        std::vector<std::string> ids;
        for (int i = 1; i < argc; ++i)
        {
            std::string a = argv[i];
            if (a == "--seconds" && i + 1 < argc)
                seconds = atof (argv[++i]);
            else
                ids.push_back (a);
        }

        [NSApplication sharedApplication];
        [NSApp setActivationPolicy:NSApplicationActivationPolicyRegular];

        int failures = 0;
        std::vector<NSWindow*> windows;
        std::vector<AudioComponentInstance> units;
        CGFloat x = 60;

        for (auto cid : ids)
        {
            // "path/to/X.component@type:sub:manu" loads an uninstalled bundle and registers its
            // factory in-process under the given description (must not clash with installed AUs)
            if (const auto at = cid.find ('@'); at != std::string::npos)
            {
                NSString* path = [NSString stringWithUTF8String:cid.substr (0, at).c_str()];
                cid = cid.substr (at + 1);

                NSBundle* bundle = [NSBundle bundleWithPath:path];
                NSDictionary* comp = [[bundle objectForInfoDictionaryKey:@"AudioComponents"] firstObject];
                NSString* factoryName = comp[@"factoryFunction"];
                NSError* error = nil;
                if (bundle == nil || factoryName == nil || ! [bundle loadAndReturnError:&error])
                {
                    printf ("[%s] FAIL: cannot load bundle %s\n", cid.c_str(), path.UTF8String);
                    ++failures;
                    continue;
                }

                auto factory = (AudioComponentFactoryFunction) CFBundleGetFunctionPointerForName (
                    CFBundleGetBundleWithIdentifier ((__bridge CFStringRef) bundle.bundleIdentifier),
                    (__bridge CFStringRef) factoryName);

                AudioComponentDescription regDesc {};
                regDesc.componentType = fourCC (cid.substr (0, 4));
                regDesc.componentSubType = fourCC (cid.substr (5, 4));
                regDesc.componentManufacturer = fourCC (cid.substr (10, 4));

                if (factory == nullptr || AudioComponentRegister (&regDesc, (__bridge CFStringRef) path.lastPathComponent, 1, factory) == nullptr)
                {
                    printf ("[%s] FAIL: cannot register factory %s\n", cid.c_str(), factoryName.UTF8String);
                    ++failures;
                    continue;
                }
            }

            AudioComponentDescription desc {};
            desc.componentType = fourCC (cid.substr (0, 4));
            desc.componentSubType = fourCC (cid.substr (5, 4));
            desc.componentManufacturer = fourCC (cid.substr (10, 4));

            AudioComponent comp = AudioComponentFindNext (nullptr, &desc);
            AudioComponentInstance unit = nullptr;
            if (comp == nullptr || AudioComponentInstanceNew (comp, &unit) != noErr)
            {
                printf ("[%s] FAIL: cannot instantiate\n", cid.c_str());
                ++failures;
                continue;
            }
            units.push_back (unit);

            UInt32 size = 0;
            Boolean writable = false;
            if (AudioUnitGetPropertyInfo (unit, kAudioUnitProperty_CocoaUI, kAudioUnitScope_Global, 0, &size, &writable) != noErr || size == 0)
            {
                printf ("[%s] FAIL: no CocoaUI property\n", cid.c_str());
                ++failures;
                continue;
            }

            std::vector<uint8_t> storage (size);
            auto* info = reinterpret_cast<AudioUnitCocoaViewInfo*> (storage.data());
            if (AudioUnitGetProperty (unit, kAudioUnitProperty_CocoaUI, kAudioUnitScope_Global, 0, info, &size) != noErr)
            {
                printf ("[%s] FAIL: CocoaUI GetProperty failed\n", cid.c_str());
                ++failures;
                continue;
            }

            NSURL* bundleURL = (__bridge_transfer NSURL*) info->mCocoaAUViewBundleLocation;
            NSString* className = (__bridge_transfer NSString*) info->mCocoaAUViewClass[0];
            NSBundle* bundle = [NSBundle bundleWithURL:bundleURL];
            Class factoryClass = [bundle classNamed:className];
            if (factoryClass == nil)
            {
                factoryClass = NSClassFromString (className);
                printf ("[%s] classNamed: returned nil, falling back to NSClassFromString\n", cid.c_str());
            }
            NSBundle* factoryBundle = factoryClass != nil ? [NSBundle bundleForClass:factoryClass] : nil;
            const bool sameBundle = factoryBundle != nil && [[factoryBundle bundleURL] isEqual:[bundle bundleURL]];

            printf ("[%s] viewClass=%s bundle=%s\n", cid.c_str(), className.UTF8String, bundleURL.lastPathComponent.UTF8String);
            printf ("[%s] resolved factory image=%s (matches AU bundle: %s)\n", cid.c_str(), imageOf (factoryClass), sameBundle ? "yes" : "NO");

            id<AUCocoaUIBase> factory = factoryClass != nil ? [[factoryClass alloc] init] : nil;
            NSView* view = factory != nil ? [factory uiViewForAudioUnit:unit withSize:NSMakeSize (400, 300)] : nil;
            if (view == nil)
            {
                printf ("[%s] FAIL: factory returned nil view\n", cid.c_str());
                ++failures;
                continue;
            }

            printf ("[%s] OK: view class=%s image=%s size=%.0fx%.0f\n", cid.c_str(),
                    NSStringFromClass ([view class]).UTF8String, imageOf ([view class]),
                    NSWidth (view.frame), NSHeight (view.frame));

            NSWindow* window = [[NSWindow alloc] initWithContentRect:NSMakeRect (x, 200, NSWidth (view.frame), NSHeight (view.frame))
                                                           styleMask:NSWindowStyleMaskTitled | NSWindowStyleMaskClosable
                                                             backing:NSBackingStoreBuffered
                                                               defer:NO];
            window.title = [NSString stringWithFormat:@"auviewhost %s", cid.c_str()];
            window.releasedWhenClosed = NO;
            window.contentView = view;
            [window makeKeyAndOrderFront:nil];
            windows.push_back (window);
            printf ("[%s] windowNumber=%ld pid=%d\n", cid.c_str(), (long) window.windowNumber, getpid());
            x += NSWidth (view.frame) + 20;
        }

        [NSApp activateIgnoringOtherApps:YES];
        fflush (stdout);
        [[NSRunLoop mainRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:seconds]];

        for (NSWindow* w : windows)
        {
            w.contentView = [[NSView alloc] init];
            [w close];
        }
        windows.clear();
        [[NSRunLoop mainRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.2]];

        for (auto unit : units)
            AudioComponentInstanceDispose (unit);

        printf ("RESULT: %s (%d failures)\n", failures == 0 ? "PASS" : "FAIL", failures);
        return failures == 0 ? 0 : 1;
    }
}
