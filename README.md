# Microsoft Surface Pro 7 Face ID research

Research into simultaneous front RGB/IR capture on Manjaro and an eventual
face-login system. Secure biometric authentication and PAD are not completed.

The [independent replacement source](replacement/README.md) implements a new
OV7251 lifecycle/readback layer on a licensed Linux baseline, a hash-bound
TensorFlow UINT8 proposal backend and tested recovery primitives. Inherited
uncertain-license OV7251 diagnostic/STROBE patches and Caffe FP16 weights are
excluded. This is an experimental source checkpoint, not an installation release.

Kernel-derived code retains GPLv2 and upstream attribution. Standalone project
userspace retains GPLv3. No firmware, pretrained weights, private photographs,
embeddings, machine credentials or private conversations are included.

See [verification evidence](replacement/TEST-EVIDENCE.json) and the
[Manjaro companion](https://github.com/BogeBear/Microsoft-Surface-Pro-7-Manjaro).
