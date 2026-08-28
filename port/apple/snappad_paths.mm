#include "snappad_paths.h"

#import <Foundation/Foundation.h>
#import <QuartzCore/CAMetalLayer.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>

#if TARGET_OS_IPHONE
#import <UIKit/UIKit.h>
#else
#import <AppKit/AppKit.h>
#endif

const char* snappad_apple_application_support_dir(void) {
    NSArray<NSURL*>* urls = [[NSFileManager defaultManager]
        URLsForDirectory:NSApplicationSupportDirectory
        inDomains:NSUserDomainMask];
    NSURL* url = [urls firstObject];
    if (url == nil) {
        return nullptr;
    }
    NSURL* snappad = [url URLByAppendingPathComponent:@"SnapPad" isDirectory:YES];
    NSError* error = nil;
    if (![[NSFileManager defaultManager] createDirectoryAtURL:snappad
                                  withIntermediateDirectories:YES
                                                   attributes:nil
                                                        error:&error]) {
        std::fprintf(stderr, "[snappad] could not create Application Support directory: %s\n",
                     [[error localizedDescription] UTF8String]);
        return nullptr;
    }
    return strdup([[snappad path] UTF8String]);
}

const char* snappad_apple_choose_rom_path(void) {
#if TARGET_OS_IPHONE
    return nullptr;
#else
    @autoreleasepool {
        NSOpenPanel* panel = [NSOpenPanel openPanel];
        panel.title = @"Choose Pokémon Snap (USA) ROM";
        panel.message = @"SnapPad accepts .z64, .v64, and .n64 files and validates the exact supported revision.";
        panel.prompt = @"Choose ROM";
        panel.canChooseDirectories = NO;
        panel.allowsMultipleSelection = NO;
        panel.allowedFileTypes = @[@"z64", @"v64", @"n64"];
        if ([panel runModal] != NSModalResponseOK || panel.URL == nil) {
            return nullptr;
        }
        return strdup([[panel.URL path] UTF8String]);
    }
#endif
}

#if TARGET_OS_IPHONE
void snappad_log_window_diagnostics(void* ui_window, void* metal_layer) {
    UIWindow* window = (__bridge UIWindow*)ui_window;
    UIScreen* screen = window.screen ?: [UIScreen mainScreen];
    CGRect bounds = window.bounds;
    CGRect frame = window.frame;
    CGRect screenBounds = screen.bounds;
    CGSize screenMode = screen.currentMode.size;
    CGSize screenNative = screen.nativeBounds.size;
    UIView* rootView = window.rootViewController.view;
    CGRect rootBounds = rootView.bounds;
    CGRect rootFrame = rootView.frame;
    CGAffineTransform windowTransform = window.transform;
    CGAffineTransform rootTransform = rootView.transform;
    NSInteger sceneOrientation = 0;
    if (@available(iOS 13.0, *)) {
        sceneOrientation = window.windowScene.interfaceOrientation;
    }
    CAMetalLayer* layer = (__bridge CAMetalLayer*)metal_layer;
    CGSize drawable = layer.drawableSize;
    std::fprintf(stderr,
        "[snappad] diag: ui_window=%p bounds=%.0fx%.0f frame=%.0fx%.0f "
        "windowTransform=[%.2f %.2f %.2f %.2f] sceneOrientation=%ld "
        "rootBounds=%.0fx%.0f rootFrame=%.0fx%.0f rootTransform=[%.2f %.2f %.2f %.2f] "
        "scale=%.2f nativeScale=%.2f "
        "screen=%.0fx%.0f mode=%.0fx%.0f native=%.0fx%.0f "
        "layer=%p drawable=%.0fx%.0f layerBounds=%.0fx%.0f layerContentsScale=%.2f\n",
        window, bounds.size.width, bounds.size.height, frame.size.width, frame.size.height,
        windowTransform.a, windowTransform.b, windowTransform.c, windowTransform.d,
        static_cast<long>(sceneOrientation),
        rootBounds.size.width, rootBounds.size.height, rootFrame.size.width, rootFrame.size.height,
        rootTransform.a, rootTransform.b, rootTransform.c, rootTransform.d,
        screen.scale, screen.nativeScale,
        screenBounds.size.width, screenBounds.size.height,
        screenMode.width, screenMode.height, screenNative.width, screenNative.height,
        layer, drawable.width, drawable.height, layer.bounds.size.width,
        layer.bounds.size.height, layer.contentsScale);
}

void snappad_fix_metal_layer_scale(void* ui_window, void* metal_layer) {
    UIWindow* window = (__bridge UIWindow*)ui_window;
    if (window == nullptr || metal_layer == nullptr) {
        return;
    }
    UIScreen* screen = window.screen ?: [UIScreen mainScreen];
    CGFloat scale = screen.nativeScale > 0.0 ? screen.nativeScale : screen.scale;
    if (scale <= 0.0) {
        return;
    }
    CAMetalLayer* layer = (__bridge CAMetalLayer*)metal_layer;
    layer.contentsScale = scale;
    CGRect bounds = window.bounds;
    layer.drawableSize = CGSizeMake(bounds.size.width * scale,
                                    bounds.size.height * scale);
}
#else
void snappad_log_window_diagnostics(void*, void*) {}
void snappad_fix_metal_layer_scale(void*, void*) {}
#endif
