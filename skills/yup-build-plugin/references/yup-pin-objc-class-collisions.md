# YUP pin and Objective-C class collisions between plugins

Read before changing the YUP revision used by EHL plugins, and when two YUP
plugins misbehave only when they are loaded in the same host process.

## Problem

Every YUP plugin image embeds its own copy of the YUP modules. If a module
declares an Objective-C class statically (`@interface Foo`), every plugin
registers `Foo` in the host's shared Objective-C runtime. The runtime keeps the
first one and prints:

```
objc[pid]: Class AudioPluginEditorViewAU is implemented in both .../a_au_plugin and .../b_au_plugin ...
```

For AUv2 this breaks the editor. `kAudioUnitProperty_CocoaUI` names the view
factory class. For the plugin loaded second, `[NSBundle classNamed:]` returns
nil, and the `NSClassFromString` fallback returns the first plugin's factory. That
factory cannot find the second plugin's AU instance, so no editor is created.
Which plugin fails depends on load order.

SDL classes had the same problem, which was fixed upstream in kunitoki/yup#112 by
the per-plugin `sdl-symbols-patch.h.in`. YUP's own classes were fixed in
kunitoki/yup#199 (opened 2026-09-28). That PR adds
`cmake/resources/objc-symbols-patch.h.in`, which is force-included next to the
SDL header and renames each class to `<target>_YupPlugin_<Class>`. It also makes
the CocoaUI property report `NSStringFromClass` of the renamed factory.

## Current EHL pin (2026-09-28)

- Revision `fa83e8c55664727ae5a53b94a3f6b5b336ce9e57` is upstream
  `9a1c9bc699b6a714f6f52486462d98a140c8bf95` plus the #199 commit
  cherry-picked, on branch `ehl/9a1c9bc-objc-class-fix` of the org fork
  `https://github.com/EsionHsrahLatigid/yup.git`. Keep that branch alive while
  any repository pins it: CI fetches it through FetchContent. (The same branch
  also exists on the personal fork `2bbb/yup`, which is the head of #199; it is
  not referenced by any pin.)
- The pin is written in these places:
  - Every plugin `CMakeLists.txt` has a FetchContent `GIT_REPOSITORY` + `GIT_TAG`.
    Some projects (CodecScar-style) also check `git rev-parse HEAD` of
    `../yup` and fail configure if it differs.
  - `yup-ehl-design-module/CMakeLists.txt` has the same FetchContent pin, used
    only for its standalone tests. The submodule pointers in the plugin repos
    were not bumped for this.
  - Build-instruction docs: README "pinned to commit" lines, LatchFault
    README/README_ja, Reverb4D THIRD_PARTY.md. DESIGN.md, reports and
    SOURCES.md record the revision that was *inspected* at the time; leave them.
  - `cmake/YupMacOSIconWorkaround.cmake` comments mention 9a1c9bc. Those remain
    true, because the fix does not touch icon generation.
- `../yup` must be checked out at the pinned commit for local builds. The
  shared checkout is used by every project, so switch it only with explicit user
  approval and update every repository in the same pass. Otherwise the
  CodecScar-style checks fail configure for projects that were not updated yet.

List every pin location with:

```sh
grep -rl <old-hash> --exclude-dir={build,_deps,output,artifacts,.git,yup,external} .
```

## When YUP is updated

1. **#199 (or an equivalent) is merged upstream and you move to that upstream
   revision:** point `GIT_REPOSITORY` back to `https://github.com/kunitoki/yup.git`,
   set the new hash everywhere listed above, and check out `../yup` at it. Then
   verify, as described below.
2. **You move to an upstream revision without the fix:** create a new branch
   from the target revision and cherry-pick the fix. Only `CHANGELOG.md` is
   expected to conflict; keep the target's file and re-add the one entry.
   Then re-scan for static classes, because new ones appear over time. Between
   9a1c9bc and 5e59b995 upstream added `YUPDraggingSource` and
   `ToastNotificationCenterDelegate`.

   ```sh
   grep -rn "^@interface [A-Za-z_]* *:\|^@implementation" modules | grep -v /thirdparty/
   ```

   Add each new class to `objc-symbols-patch.h.in` unless it is looked up by a
   string that the patch cannot rename:
   - `YUPAUv3ViewController` is `NSExtensionPrincipalClass` in the AUv3 plist.
   - `YupApplicationDelegate` is application-only.

   Classes built with `ObjCClass<...>` get randomized names and are safe.
   Push the branch to the org fork `EsionHsrahLatigid/yup` and pin its full hash. Never pin a branch name.

## Verification

1. Build two AUv2 plugins from the fixed revision. Build them into a scratch
   build directory and do not install them over the user's plugins. For EHL
   projects, pass `-D<PROJECT>_BUILD_PLUGIN=ON
   -D<PROJECT>_YUP_SOURCE_DIR=<fixed worktree>` and build the
   `<slug>_au_plugin` target.
2. Check the class names in each bundle. Every YUP and SDL class must carry
   the target prefix:

   ```sh
   otool -v -s __TEXT __objc_classname <bundle>/Contents/MacOS/<exe> | tr -s ' \t' '\n' \
     | grep -i "AudioPlugin\|Dragging\|Toast\|SDL"
   ```

3. Open both editors in one process with [../scripts/auviewhost.mm](../scripts/auviewhost.mm).
   Use `bundle@type:sub:manu` with IDs that are not installed, so the user's
   installed plugins are not touched. Try both load orders.
   Pass criteria:
   - no `implemented in both` on stderr
   - `RESULT: PASS`
   - `viewClass` is `<target>_YupPlugin_AudioPluginProcessorAUViewFactory`
4. Capture both windows (`screencapture -x -o -l <windowNumber>`) to confirm
   native rendering. Mouse and keyboard input to the editors is a separate claim;
   report it as a gap unless it was exercised in a real host.
5. Run `auval -v <type> <sub> <manu>` on installed builds before release.

## Pitfalls

- **CMake de-duplicates compile options.** Two bare `-include <file>` pairs lose
  the second `-include`, and clang fails with "cannot specify -o when generating
  multiple output files". #199 changed the force-include to
  `SHELL:-include "<file>"`. Keep that form when adding headers.
- **Do not convert the AU view factory to a runtime `ObjCClass`.**
  `bundleForClass:` on a runtime class returns the host's main bundle, and the
  CocoaUI property needs the plugin bundle URL.
- **Configure a scratch project that embeds YUP with
  `project(... LANGUAGES C CXX OBJC OBJCXX)`.** Without ObjC/ObjC++, CMake
  reports that `CMAKE_OBJCXX_COMPILE_OBJECT` is missing.
- **Run with `LANG`/`LC_ALL=en_US.UTF-8`.** Otherwise the flac upstream archive
  fails to extract ("Pathname can't be converted from UTF-8").
- **YUP's own `CLAUDE.md` tells AI agents not to build or test inside the
  YUP repo.** Build verification projects outside it, and say in any upstream
  PR how it was verified.
