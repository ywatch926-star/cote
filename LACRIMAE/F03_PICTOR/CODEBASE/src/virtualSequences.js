export function normalizeSequences(manifest) {
  if (!manifest) return [];
  const rows = Array.isArray(manifest) ? manifest : (manifest.sequences || manifest.candidate_sequences || []);
  return rows
    .map((row, index) => ({
      id: row.id || `seq_${String(index + 1).padStart(4, '0')}`,
      sourceStartFrame: Math.max(0, Number(row.source_start_frame ?? row.start_frame ?? 0)),
      timelineStartFrame: Math.max(0, Number(row.timeline_start_frame ?? index * Number(manifest.cut_interval_frames || 7))),
      durationFrames: Math.max(1, Number(row.timeline_duration_frames ?? row.duration_frames ?? manifest.cut_interval_frames ?? 7)),
      rotationDeg: row.rotation_deg == null ? null : Number(row.rotation_deg),
      fit: row.fit || null,
      rotationLayer: row.rotation_layer || row.layer || null,
      muted: row.muted !== false,
    }))
    .filter((row) => Number.isFinite(row.sourceStartFrame) && Number.isFinite(row.timelineStartFrame));
}

export function manifestDuration(manifest, fallback = 300) {
  return Number(manifest?.total_frames) > 0 ? Number(manifest.total_frames) : fallback;
}
