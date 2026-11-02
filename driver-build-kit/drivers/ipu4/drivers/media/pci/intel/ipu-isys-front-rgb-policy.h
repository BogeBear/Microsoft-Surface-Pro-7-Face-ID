/* SPDX-License-Identifier: GPL-2.0 */
/*
 * SP7 IR project modification notice.
 * New GPLv2 project helper for the Intel IPU4/SP7 camera stack.
 * Documented project source/patch records:
 * 2026-10-19: New SP7 front-RGB route and bounded start-abort helper.
 * Dates identify retained records, not exact original edit timestamps.
 * 2026-10-23: This modification notice added.
 * Original copyright and license notices are retained.
 * Repository-root references:
 * IPU4-PROVENANCE.json (source revisions and per-file comparisons).
 * IPU4-DATED-CHANGES.json (dated records and checksum bindings).
 * patches/ipu4-source-changes.patch (changes against September port).
 */

#ifndef IPU_ISYS_FRONT_RGB_POLICY_H
#define IPU_ISYS_FRONT_RGB_POLICY_H
/* Call after the isys, CSI-2, bus and platform declarations are available. */
static inline bool ipu_isys_front_rgb_start_route(struct ipu_isys_pipeline *ip)
{
#ifdef CONFIG_VIDEO_INTEL_IPU4P
 return ip && ip->csi2 && ip->csi2->isys && ip->csi2->isys->adev &&
        ip->csi2->index == 2 && ip->csi2->nlanes == 2 &&
        ip->source == IPU_FW_ISYS_STREAM_SRC_CSI2_PORT0 + 7 &&
        ip->nr_queues == 1 && !ip->interlaced && ip->external &&
        ip->external->entity &&
        str_has_prefix(ip->external->entity->name, "ov5693 ") &&
        ipu4p_isys_get_quirks(&ip->csi2->isys->adev->dev);
#else
 return false;
#endif
}
static inline bool ipu_isys_front_rgb_abort_start(struct ipu_isys_pipeline *ip)
{
 return ipu_isys_front_rgb_start_route(ip) && atomic_read(&ip->verify_active);
}
#endif
