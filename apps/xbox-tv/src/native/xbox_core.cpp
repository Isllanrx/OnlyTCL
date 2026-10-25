#include <jni.h>
#include <sys/resource.h>
#include <unistd.h>
#include <pthread.h>
#include <android/log.h>
#include <string.h>
#include <stdio.h>
#include <stdint.h>

#define TAG "XboxNativeCore"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, TAG, __VA_ARGS__)
#define LOGW(...) __android_log_print(ANDROID_LOG_WARN, TAG, __VA_ARGS__)

#pragma pack(push, 4)
typedef struct {
    float lx;
    float ly;
    float rx;
    float ry;
    float lt;
    float rt;
    float hatX;
    float hatY;
    uint32_t buttons;
    uint32_t connected;
    uint64_t timestamp_ns;
} NativeGamepadState;
#pragma pack(pop)

static NativeGamepadState g_state = {0};
static pthread_mutex_t g_lock = PTHREAD_MUTEX_INITIALIZER;
static char g_json_scratch[1024];

static inline uint64_t get_time_ns() {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ((uint64_t)ts.tv_sec * 1000000000ULL) + (uint64_t)ts.tv_nsec;
}

extern "C" {

JNIEXPORT void JNICALL
Java_gamepass_fire_tv_NativeInputEngine_boostPriority(JNIEnv* env, jclass clazz) {
    // Elevate priority of current thread to maximum real-time priority (nice -20)
    int ret = setpriority(PRIO_PROCESS, 0, -20);
    if (ret == 0) {
        LOGI("Native input thread priority boosted to real-time (nice -20).");
    } else {
        LOGW("Failed to set priority -20, attempting -10");
        setpriority(PRIO_PROCESS, 0, -10);
    }
}

JNIEXPORT void JNICALL
Java_gamepass_fire_tv_NativeInputEngine_updateAxes(
    JNIEnv* env, jclass clazz,
    jfloat lx, jfloat ly, jfloat rx, jfloat ry,
    jfloat lt, jfloat rt, jfloat hatX, jfloat hatY
) {
    pthread_mutex_lock(&g_lock);
    g_state.lx = lx;
    g_state.ly = ly;
    g_state.rx = rx;
    g_state.ry = ry;
    g_state.lt = lt;
    g_state.rt = rt;
    g_state.hatX = hatX;
    g_state.hatY = hatY;
    g_state.timestamp_ns = get_time_ns();
    pthread_mutex_unlock(&g_lock);
}

JNIEXPORT void JNICALL
Java_gamepass_fire_tv_NativeInputEngine_updateButton(
    JNIEnv* env, jclass clazz,
    jint buttonMask, jboolean pressed
) {
    pthread_mutex_lock(&g_lock);
    if (pressed) {
        g_state.buttons |= (uint32_t)buttonMask;
    } else {
        g_state.buttons &= ~((uint32_t)buttonMask);
    }
    g_state.timestamp_ns = get_time_ns();
    pthread_mutex_unlock(&g_lock);
}

JNIEXPORT void JNICALL
Java_gamepass_fire_tv_NativeInputEngine_setConnected(
    JNIEnv* env, jclass clazz,
    jboolean connected
) {
    pthread_mutex_lock(&g_lock);
    g_state.connected = connected ? 1 : 0;
    g_state.timestamp_ns = get_time_ns();
    pthread_mutex_unlock(&g_lock);
}

JNIEXPORT jstring JNICALL
Java_gamepass_fire_tv_NativeInputEngine_getFastJson(JNIEnv* env, jclass clazz) {
    NativeGamepadState copy;
    pthread_mutex_lock(&g_lock);
    memcpy(&copy, &g_state, sizeof(NativeGamepadState));
    pthread_mutex_unlock(&g_lock);

    // Fast C-level JSON serialization with zero Java allocations
    int len = snprintf(
        g_json_scratch, sizeof(g_json_scratch),
        "{\"c\":%u,\"ts\":%llu,\"axes\":[%.4f,%.4f,%.4f,%.4f],\"lt\":%.4f,\"rt\":%.4f,\"hx\":%.1f,\"hy\":%.1f,\"b\":%u}",
        copy.connected,
        (unsigned long long)copy.timestamp_ns,
        copy.lx, copy.ly, copy.rx, copy.ry,
        copy.lt, copy.rt, copy.hatX, copy.hatY,
        copy.buttons
    );

    if (len < 0 || len >= (int)sizeof(g_json_scratch)) {
        return env->NewStringUTF("{}");
    }
    return env->NewStringUTF(g_json_scratch);
}

} // extern "C"
