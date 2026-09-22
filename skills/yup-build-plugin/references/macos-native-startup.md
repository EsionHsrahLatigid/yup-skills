# macOS standalone startup and native GUI verification

Read for YUP macOS standalone startup/event-loop changes or failed external GUI
inspection. Missing AppKit initialization is a general custom-loop failure mode;
the YUP/SDL sequence below is one demonstrated instance, not a universal YUP bug.

## Acceptance evidence

Use the exact staged bundle path, especially when preview and normal builds share
a bundle ID. Record the current executable/PID and source revisions. Check native
window retrieval and an affected control interaction through the supported UI
tool; observe the resulting state. A first click may only focus a background
window. Keep audio monitoring/test pulses off unless the task calls for them.

Keep four claims distinct: compiled/tested, rendered offscreen, externally
inspectable, and operable through native input. A running process,
`NSRunningApplication.isFinishedLaunching`, or app inventory is not a substitute
for the last two. Standalone success does not prove VST3/AU-host GUI behavior.

## Bounded diagnosis

1. Compare the failing target with a known-good app through the same connector.
   A control success localizes the problem; it does not prove the precise cause.
2. If the failure repeats, investigate a different layer instead of extending
   timeouts or repeatedly restarting. A connector timeout, AX messaging error,
   missing server registration, and missing custom-control AX children are
   different observations. Do not label them all permission failures or deadlocks.
3. Where available, inspect only the current application's PID and `pid-local
   endpoints` from its discovered `launchctl print gui/<uid>/<application-label>`
   service. Compare `com.apple.axserver` with the control app. Discover labels and
   PIDs afresh; filter output, since full service dumps may contain environment
   values. Absence/presence is diagnostic evidence, not a portable public API or
   sufficient acceptance test. Missing launchctl information is inconclusive.
4. Inspect the pinned startup sources: who creates NSApp, owns its delegate,
   completes launch, and drives events? Rendering alone does not prove that
   AppKit initialization was completed. Prove a candidate with an audio-free,
   bounded minimal reproduction before changing shared framework behavior.

Follow the UI tool's documented access rules; do not substitute an unauthorized
AX/AppleScript automation path. Preserve unsaved state. Do not change TCC,
permissions, private AX registration APIs, or other apps to make a check pass.

## Demonstrated YUP/SDL case and repair boundaries

Reverb4D (2026-09-22), YUP `9a1c9bc699b6a714f6f52486462d98a140c8bf95`,
SDL `f87239e71e42da91ca317a12eefb82cfbf3393eb`:

- YUP `modules/yup_events/native/yup_MessageManager_mac.mm` creates NSApplication
  early and uses a custom CFRunLoop instead of `NSApplication.run`.
- SDL `src/video/cocoa/SDL_cocoaevents.m`, `Cocoa_RegisterApp`, calls
  `finishLaunching` only when NSApp is initially absent. The early YUP creation
  skips that branch.
- Audio-free comparison: shared NSApp + custom loop without launch completion
  had no AX endpoint and timed out; explicit `finishLaunching` and standard
  `NSApplication.run` both registered the endpoint and allowed AX retrieval.
- A main-thread, once-only completion in the Reverb4D standalone adapter restored
  actual CUA capture and interaction. It did not add custom-control AX semantics.

Re-inspect these paths after dependency upgrades. Do not add `finishLaunching`
unconditionally or infer all YUP versions/consumers need this helper. A plugin
does not own its host's NSApplication: no such call in VST3/AU/shared processor or
editor code. A confirmed consumer-only workaround is narrower than modifying a
shared checkout; an upstream change requires its own scope and validation.

## Regression shape

For a confirmed standalone lifecycle repair, test launch completion and
idempotency without audio. The Reverb4D test observes the synchronous
`NSApplicationWillFinishLaunchingNotification`: no-op baseline fails, actual
helper fires once across two calls. Do not assume did-finish is synchronous.
Then verify the actual staged app's AX/capture and representative interactions;
notification tests alone cannot prove those. Retain ordinary plugin/DSP tests.

Primary API source: [Apple finishLaunching](https://developer.apple.com/documentation/appkit/nsapplication/finishlaunching%28%29).
Case evidence: Reverb4D commit `3e186887e2ab5728e24fddf18240a280a87af4e2`,
`reports/macos-appkit-lifecycle-2026-09-22.md`; Obsidian
`yup/Reverb4D/04 Verification and Release.md`.
