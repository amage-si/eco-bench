// VK_LAYER_AMAGE_present_log: a minimal explicit Vulkan layer that records
// when each frame is handed to the presentation engine, for benchmarks.
//
// For every vkQueuePresentKHR it appends a line with CLOCK_MONOTONIC (ns) on
// entry and on return, the result and the swapchain; for every
// vkAcquireNextImageKHR the same; for every vkCreateSwapchainKHR the new
// swapchain's extent and present mode. Lines go to the file named by
// AMAGE_PRESENT_LOG (appended); without it the layer only passes calls on.
//
// Enable it per process, without touching system configuration:
//   VK_LAYER_PATH=<dir with the manifest> VK_INSTANCE_LAYERS=VK_LAYER_AMAGE_present_log
//
// No Vulkan headers are needed: the few types it touches are declared here
// with the layouts of the Vulkan and loader-layer headers (vulkan_core.h,
// vk_layer.h).

#include <pthread.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <fcntl.h>
#include <unistd.h>

#define EXPORT __attribute__((visibility("default")))

typedef int32_t VkResult;
typedef int32_t VkStructureType;
typedef uint32_t VkFlags;
typedef uint32_t VkBool32;
typedef uint64_t VkSwapchainKHR;
typedef uint64_t VkSurfaceKHR;
typedef uint64_t VkSemaphore;
typedef uint64_t VkFence;
typedef struct VkInstance_T *VkInstance;
typedef struct VkPhysicalDevice_T *VkPhysicalDevice;
typedef struct VkDevice_T *VkDevice;
typedef struct VkQueue_T *VkQueue;
typedef struct VkAllocationCallbacks VkAllocationCallbacks;

typedef void (*PFN_vkVoidFunction)(void);
typedef PFN_vkVoidFunction (*PFN_vkGetInstanceProcAddr)(VkInstance, const char *);
typedef PFN_vkVoidFunction (*PFN_vkGetDeviceProcAddr)(VkDevice, const char *);
typedef PFN_vkVoidFunction (*PFN_GetPhysicalDeviceProcAddr)(VkInstance, const char *);

enum {
  VK_SUCCESS = 0,
  VK_ERROR_INITIALIZATION_FAILED = -3,
  VK_STRUCTURE_TYPE_LOADER_INSTANCE_CREATE_INFO = 47,
  VK_STRUCTURE_TYPE_LOADER_DEVICE_CREATE_INFO = 48,
  VK_LAYER_LINK_INFO = 0,
  LAYER_NEGOTIATE_INTERFACE_STRUCT = 1,
};

typedef struct VkBaseIn {
  VkStructureType sType;
  const struct VkBaseIn *pNext;
} VkBaseIn;

typedef struct VkLayerInstanceLink {
  struct VkLayerInstanceLink *pNext;
  PFN_vkGetInstanceProcAddr pfnNextGetInstanceProcAddr;
  PFN_GetPhysicalDeviceProcAddr pfnNextGetPhysicalDeviceProcAddr;
} VkLayerInstanceLink;

typedef struct VkLayerInstanceCreateInfo {
  VkStructureType sType;
  const void *pNext;
  int32_t function;
  union {
    VkLayerInstanceLink *pLayerInfo;
    struct { void *a; void *b; } other;
  } u;
} VkLayerInstanceCreateInfo;

typedef struct VkLayerDeviceLink {
  struct VkLayerDeviceLink *pNext;
  PFN_vkGetInstanceProcAddr pfnNextGetInstanceProcAddr;
  PFN_vkGetDeviceProcAddr pfnNextGetDeviceProcAddr;
} VkLayerDeviceLink;

typedef struct VkLayerDeviceCreateInfo {
  VkStructureType sType;
  const void *pNext;
  int32_t function;
  union {
    VkLayerDeviceLink *pLayerInfo;
    void *other;
  } u;
} VkLayerDeviceCreateInfo;

typedef struct VkNegotiateLayerInterface {
  int32_t sType;
  void *pNext;
  uint32_t loaderLayerInterfaceVersion;
  PFN_vkGetInstanceProcAddr pfnGetInstanceProcAddr;
  PFN_vkGetDeviceProcAddr pfnGetDeviceProcAddr;
  PFN_GetPhysicalDeviceProcAddr pfnGetPhysicalDeviceProcAddr;
} VkNegotiateLayerInterface;

typedef struct VkExtent2D {
  uint32_t width;
  uint32_t height;
} VkExtent2D;

typedef struct VkSwapchainCreateInfoKHR {
  VkStructureType sType;
  const void *pNext;
  VkFlags flags;
  VkSurfaceKHR surface;
  uint32_t minImageCount;
  int32_t imageFormat;
  int32_t imageColorSpace;
  VkExtent2D imageExtent;
  uint32_t imageArrayLayers;
  VkFlags imageUsage;
  int32_t imageSharingMode;
  uint32_t queueFamilyIndexCount;
  const uint32_t *pQueueFamilyIndices;
  int32_t preTransform;
  int32_t compositeAlpha;
  int32_t presentMode;
  VkBool32 clipped;
  VkSwapchainKHR oldSwapchain;
} VkSwapchainCreateInfoKHR;

typedef struct VkPresentInfoKHR {
  VkStructureType sType;
  const void *pNext;
  uint32_t waitSemaphoreCount;
  const VkSemaphore *pWaitSemaphores;
  uint32_t swapchainCount;
  const VkSwapchainKHR *pSwapchains;
  const uint32_t *pImageIndices;
  VkResult *pResults;
} VkPresentInfoKHR;

typedef VkResult (*PFN_vkCreateInstance)(const VkBaseIn *, const VkAllocationCallbacks *, VkInstance *);
typedef VkResult (*PFN_vkCreateDevice)(VkPhysicalDevice, const VkBaseIn *, const VkAllocationCallbacks *, VkDevice *);
typedef VkResult (*PFN_vkQueuePresentKHR)(VkQueue, const VkPresentInfoKHR *);
typedef VkResult (*PFN_vkCreateSwapchainKHR)(VkDevice, const VkSwapchainCreateInfoKHR *, const VkAllocationCallbacks *,
                                             VkSwapchainKHR *);
typedef VkResult (*PFN_vkAcquireNextImageKHR)(VkDevice, VkSwapchainKHR, uint64_t, VkSemaphore, VkFence, uint32_t *);

// Per-instance and per-device state, keyed by the loader's dispatch pointer
// (the first word of every dispatchable handle; a device's queues share it).

#define MAX_OBJECTS 16

typedef struct {
  void *key;
  VkInstance instance;
  PFN_vkGetInstanceProcAddr gipa;
} InstanceData;

typedef struct {
  void *key;
  VkDevice device;
  PFN_vkGetDeviceProcAddr gdpa;
  PFN_vkQueuePresentKHR present;
  PFN_vkCreateSwapchainKHR create_swapchain;
  PFN_vkAcquireNextImageKHR acquire;
} DeviceData;

static InstanceData instances[MAX_OBJECTS];
static DeviceData devices[MAX_OBJECTS];
static int instance_count, device_count;
static pthread_mutex_t table_lock = PTHREAD_MUTEX_INITIALIZER;

static void *key_of(const void *handle) { return *(void *const *)handle; }

static InstanceData *find_instance(void *key) {
  for (int i = 0; i < instance_count; i++)
    if (instances[i].key == key) return &instances[i];
  return instance_count > 0 ? &instances[instance_count - 1] : NULL;
}

static DeviceData *find_device(void *key) {
  for (int i = 0; i < device_count; i++)
    if (devices[i].key == key) return &devices[i];
  return NULL;
}

// Logging

static int log_fd = -2;
static pthread_once_t log_once = PTHREAD_ONCE_INIT;

static uint64_t now_ns(void) {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (uint64_t)ts.tv_sec * 1000000000ull + (uint64_t)ts.tv_nsec;
}

static void open_log(void) {
  const char *path = getenv("AMAGE_PRESENT_LOG");
  log_fd = path && *path ? open(path, O_WRONLY | O_CREAT | O_APPEND | O_CLOEXEC, 0644) : -1;
}

static void put(const char *fmt, ...) __attribute__((format(printf, 1, 2)));

static void put(const char *fmt, ...) {
  pthread_once(&log_once, open_log);
  if (log_fd < 0) return;
  char line[256];
  va_list ap;
  va_start(ap, fmt);
  int n = vsnprintf(line, sizeof line, fmt, ap);
  va_end(ap);
  if (n > 0) {
    ssize_t ignored = write(log_fd, line, (size_t)(n < (int)sizeof line ? n : (int)sizeof line - 1));
    (void)ignored;
  }
}

// Intercepted calls

static VkResult layer_QueuePresentKHR(VkQueue queue, const VkPresentInfoKHR *info) {
  DeviceData *d = find_device(key_of(queue));
  uint64_t t0 = now_ns();
  VkResult r = d->present(queue, info);
  uint64_t t1 = now_ns();
  put("present %llu %llu %d %llx %u\n", (unsigned long long)t0, (unsigned long long)t1, r,
      (unsigned long long)(info->swapchainCount ? info->pSwapchains[0] : 0),
      info->swapchainCount && info->pImageIndices ? info->pImageIndices[0] : 0);
  return r;
}

static VkResult layer_AcquireNextImageKHR(VkDevice device, VkSwapchainKHR swapchain, uint64_t timeout,
                                          VkSemaphore semaphore, VkFence fence, uint32_t *index) {
  DeviceData *d = find_device(key_of(device));
  uint64_t t0 = now_ns();
  VkResult r = d->acquire(device, swapchain, timeout, semaphore, fence, index);
  uint64_t t1 = now_ns();
  put("acquire %llu %llu %d %llx %u\n", (unsigned long long)t0, (unsigned long long)t1, r,
      (unsigned long long)swapchain, index ? *index : 0);
  return r;
}

static VkResult layer_CreateSwapchainKHR(VkDevice device, const VkSwapchainCreateInfoKHR *info,
                                         const VkAllocationCallbacks *alloc, VkSwapchainKHR *out) {
  DeviceData *d = find_device(key_of(device));
  uint64_t t0 = now_ns();
  VkResult r = d->create_swapchain(device, info, alloc, out);
  uint64_t t1 = now_ns();
  put("swapchain %llu %llu %d %llx %ux%u mode %d images %u\n", (unsigned long long)t0, (unsigned long long)t1, r,
      (unsigned long long)(r == VK_SUCCESS ? *out : 0), info->imageExtent.width, info->imageExtent.height,
      info->presentMode, info->minImageCount);
  return r;
}

static PFN_vkVoidFunction layer_GetDeviceProcAddr(VkDevice device, const char *name);
static PFN_vkVoidFunction layer_GetInstanceProcAddr(VkInstance instance, const char *name);

static VkResult layer_CreateInstance(const VkBaseIn *info, const VkAllocationCallbacks *alloc, VkInstance *out) {
  VkLayerInstanceCreateInfo *chain = (VkLayerInstanceCreateInfo *)info->pNext;
  while (chain && !(chain->sType == VK_STRUCTURE_TYPE_LOADER_INSTANCE_CREATE_INFO &&
                    chain->function == VK_LAYER_LINK_INFO))
    chain = (VkLayerInstanceCreateInfo *)chain->pNext;
  if (!chain) return VK_ERROR_INITIALIZATION_FAILED;
  PFN_vkGetInstanceProcAddr gipa = chain->u.pLayerInfo->pfnNextGetInstanceProcAddr;
  chain->u.pLayerInfo = chain->u.pLayerInfo->pNext;
  PFN_vkCreateInstance create = (PFN_vkCreateInstance)gipa(NULL, "vkCreateInstance");
  if (!create) return VK_ERROR_INITIALIZATION_FAILED;
  uint64_t t0 = now_ns();
  VkResult r = create(info, alloc, out);
  uint64_t t1 = now_ns();
  if (r == VK_SUCCESS) {
    pthread_mutex_lock(&table_lock);
    if (instance_count < MAX_OBJECTS) instances[instance_count++] = (InstanceData){key_of(*out), *out, gipa};
    pthread_mutex_unlock(&table_lock);
  }
  put("instance %llu %llu %d pid %d\n", (unsigned long long)t0, (unsigned long long)t1, r, (int)getpid());
  return r;
}

static VkResult layer_CreateDevice(VkPhysicalDevice physical, const VkBaseIn *info, const VkAllocationCallbacks *alloc,
                                   VkDevice *out) {
  VkLayerDeviceCreateInfo *chain = (VkLayerDeviceCreateInfo *)info->pNext;
  while (chain && !(chain->sType == VK_STRUCTURE_TYPE_LOADER_DEVICE_CREATE_INFO &&
                    chain->function == VK_LAYER_LINK_INFO))
    chain = (VkLayerDeviceCreateInfo *)chain->pNext;
  if (!chain) return VK_ERROR_INITIALIZATION_FAILED;
  PFN_vkGetInstanceProcAddr gipa = chain->u.pLayerInfo->pfnNextGetInstanceProcAddr;
  PFN_vkGetDeviceProcAddr gdpa = chain->u.pLayerInfo->pfnNextGetDeviceProcAddr;
  chain->u.pLayerInfo = chain->u.pLayerInfo->pNext;
  InstanceData *inst = find_instance(key_of(physical));
  PFN_vkCreateDevice create = (PFN_vkCreateDevice)gipa(inst ? inst->instance : NULL, "vkCreateDevice");
  if (!create) return VK_ERROR_INITIALIZATION_FAILED;
  uint64_t t0 = now_ns();
  VkResult r = create(physical, info, alloc, out);
  uint64_t t1 = now_ns();
  if (r == VK_SUCCESS) {
    DeviceData d = {key_of(*out), *out, gdpa,
                    (PFN_vkQueuePresentKHR)gdpa(*out, "vkQueuePresentKHR"),
                    (PFN_vkCreateSwapchainKHR)gdpa(*out, "vkCreateSwapchainKHR"),
                    (PFN_vkAcquireNextImageKHR)gdpa(*out, "vkAcquireNextImageKHR")};
    pthread_mutex_lock(&table_lock);
    if (device_count < MAX_OBJECTS) devices[device_count++] = d;
    pthread_mutex_unlock(&table_lock);
  }
  put("device %llu %llu %d\n", (unsigned long long)t0, (unsigned long long)t1, r);
  return r;
}

static PFN_vkVoidFunction device_hook(DeviceData *d, const char *name) {
  if (!strcmp(name, "vkQueuePresentKHR")) return d && d->present ? (PFN_vkVoidFunction)layer_QueuePresentKHR : NULL;
  if (!strcmp(name, "vkCreateSwapchainKHR"))
    return d && d->create_swapchain ? (PFN_vkVoidFunction)layer_CreateSwapchainKHR : NULL;
  if (!strcmp(name, "vkAcquireNextImageKHR")) return d && d->acquire ? (PFN_vkVoidFunction)layer_AcquireNextImageKHR : NULL;
  return NULL;
}

static int is_hooked_device_call(const char *name) {
  return !strcmp(name, "vkQueuePresentKHR") || !strcmp(name, "vkCreateSwapchainKHR") ||
         !strcmp(name, "vkAcquireNextImageKHR");
}

static PFN_vkVoidFunction layer_GetDeviceProcAddr(VkDevice device, const char *name) {
  if (!strcmp(name, "vkGetDeviceProcAddr")) return (PFN_vkVoidFunction)layer_GetDeviceProcAddr;
  DeviceData *d = device ? find_device(key_of(device)) : NULL;
  if (is_hooked_device_call(name)) return device_hook(d, name);
  return d ? d->gdpa(device, name) : NULL;
}

static PFN_vkVoidFunction layer_GetInstanceProcAddr(VkInstance instance, const char *name) {
  if (!strcmp(name, "vkGetInstanceProcAddr")) return (PFN_vkVoidFunction)layer_GetInstanceProcAddr;
  if (!strcmp(name, "vkCreateInstance")) return (PFN_vkVoidFunction)layer_CreateInstance;
  if (!strcmp(name, "vkCreateDevice")) return (PFN_vkVoidFunction)layer_CreateDevice;
  if (!strcmp(name, "vkGetDeviceProcAddr")) return (PFN_vkVoidFunction)layer_GetDeviceProcAddr;
  if (is_hooked_device_call(name) && device_count > 0) return device_hook(&devices[0], name);
  InstanceData *inst = instance ? find_instance(key_of(instance)) : NULL;
  return inst ? inst->gipa(instance, name) : NULL;
}

EXPORT VkResult vkNegotiateLoaderLayerInterfaceVersion(VkNegotiateLayerInterface *v) {
  if (!v || v->sType != LAYER_NEGOTIATE_INTERFACE_STRUCT) return VK_ERROR_INITIALIZATION_FAILED;
  if (v->loaderLayerInterfaceVersion >= 2) {
    v->pfnGetInstanceProcAddr = layer_GetInstanceProcAddr;
    v->pfnGetDeviceProcAddr = layer_GetDeviceProcAddr;
    v->pfnGetPhysicalDeviceProcAddr = NULL;
  }
  if (v->loaderLayerInterfaceVersion > 2) v->loaderLayerInterfaceVersion = 2;
  return VK_SUCCESS;
}
