/* SPDX-License-Identifier: GPL-2.0 */
/*
 * SP7 IR project modification notice.
 * New GPLv2 project helper for the Intel IPU4/SP7 camera stack.
 * Documented project source/patch records:
 * 2026-10-19: New helper separates link-validation context from pad
 * ownership.
 * Dates identify retained records, not exact original edit timestamps.
 * 2026-10-23: This modification notice added.
 * Original copyright and license notices are retained.
 * Repository-root references:
 * IPU4-PROVENANCE.json (source revisions and per-file comparisons).
 * IPU4-DATED-CHANGES.json (dated records and checksum bindings).
 * patches/ipu4-source-changes.patch (changes against September port).
 */

#ifndef IPU_ISYS_PIPELINE_CONTEXT_H
#define IPU_ISYS_PIPELINE_CONTEXT_H
/* The caller serializes validating with media_dev.graph_mutex. The media
 * core validates links before publishing pad->pipe; no ownership is forged.
 * Outside that synchronous callback, use only actual per-pad ownership.
 */
static inline struct media_pipeline *
ipu_isys_link_pipeline(struct media_pad *sink,
		       struct media_pipeline *validating)
{
	return validating ? validating : media_pad_pipeline(sink);
}
#endif
