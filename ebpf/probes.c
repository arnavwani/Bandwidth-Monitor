#include <uapi/linux/ptrace.h>

struct data_t {
    u32 pid;
    u64 bytes;
    char comm[16];
    u8 direction; // 0 = send, 1 = recv
};

BPF_PERF_OUTPUT(events);

int trace_sendto(struct pt_regs *ctx, int fd, void *buff, size_t len) {
    struct data_t data = {};
    data.pid = bpf_get_current_pid_tgid() >> 32;
    data.bytes = len;
    data.direction = 0;
    bpf_get_current_comm(&data.comm, sizeof(data.comm));
    events.perf_submit(ctx, &data, sizeof(data));
    return 0;
}

int trace_recvfrom(struct pt_regs *ctx) {
    int ret = PT_REGS_RC(ctx);
    if (ret <= 0) return 0;
    struct data_t data = {};
    data.pid = bpf_get_current_pid_tgid() >> 32;
    data.bytes = ret;
    data.direction = 1;
    bpf_get_current_comm(&data.comm, sizeof(data.comm));
    events.perf_submit(ctx, &data, sizeof(data));
    return 0;
}
