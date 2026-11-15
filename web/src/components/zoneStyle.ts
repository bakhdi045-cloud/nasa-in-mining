// Outline styles of the study zones, shared by the map and its legend.
export const ZONE_STYLE: Record<string, { color: string; width: number; dash?: number[]; key: string }> = {
  study_perimeter: { color: "#ffffff", width: 2.4, key: "legend.study" },
  control_ring: { color: "#f4d35e", width: 1.4, dash: [2, 2], key: "legend.control" },
  mapped_mining_outside_perimeter: { color: "#ff7ad9", width: 1.4, key: "legend.panels" },
};
