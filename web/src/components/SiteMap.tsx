import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import { Layers, MapPin } from "lucide-react";
import type { Measurement, Site } from "../types";
import { siteLetter } from "../analysis";

type Props = {
  sites: Site[];
  measurements: Measurement[];
  lowest: string[];
  onSelect: (name: string) => void;
  selected: string | null;
};
export function SiteMap({
  sites,
  measurements,
  lowest,
  onSelect,
  selected,
}: Props) {
  const element = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  const group = useRef<L.LayerGroup | null>(null);
  const locationKey = useRef("");
  const [tileError, setTileError] = useState(false);
  useEffect(() => {
    if (!element.current) return;
    const instance = L.map(element.current, {
      zoomControl: false,
      scrollWheelZoom: false,
    }).setView([33.46, -112.005], 11);
    const tiles = L.tileLayer(
      "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
      {
        maxZoom: 19,
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      },
    ).addTo(instance);
    tiles.on("tileerror", () => setTileError(true));
    L.control.zoom({ position: "bottomright" }).addTo(instance);
    map.current = instance;
    group.current = L.layerGroup().addTo(instance);
    const observer = new ResizeObserver(() => instance.invalidateSize());
    observer.observe(element.current);
    return () => {
      observer.disconnect();
      instance.remove();
      map.current = null;
      group.current = null;
    };
  }, []);
  useEffect(() => {
    if (!map.current || !group.current) return;
    group.current.clearLayers();
    sites.forEach((site, index) => {
      const value = measurements.find(
        (item) => item.name === site.name,
      )?.temperature_c;
      const isLowest = lowest.includes(site.name);
      const letter = siteLetter(site.name, index);
      const icon = L.divIcon({
        className: "site-map-pin",
        html: `<span class="map-dot ${isLowest ? "lowest" : ""} ${selected === site.name ? "selected" : ""}">${letter}</span>${value != null ? `<span class="map-value">${value.toFixed(1)}°</span>` : ""}`,
        iconSize: [44, 44],
        iconAnchor: [22, 22],
      });
      const tooltip = document.createElement("span");
      tooltip.textContent = site.name;
      L.marker([site.latitude, site.longitude], {
        icon,
        title: site.name,
        alt: site.name,
      })
        .bindTooltip(tooltip, { direction: "top", offset: [0, -20] })
        .on("click", () => onSelect(site.name))
        .addTo(group.current!);
    });
    const key = sites
      .map((site) => `${site.latitude},${site.longitude}`)
      .join(";");
    if (sites.length && key !== locationKey.current) {
      map.current.fitBounds(
        L.latLngBounds(
          sites.map((site) => [site.latitude, site.longitude] as L.LatLngTuple),
        ),
        { padding: [64, 64], maxZoom: 12 },
      );
      locationKey.current = key;
    }
  }, [sites, measurements, lowest, onSelect, selected]);
  return (
    <section className="map-card" aria-label="Selected locations map">
      <div ref={element} className="site-map" />
      <div className="map-caption">
        <span className="map-caption-icon">
          <MapPin size={16} />
        </span>
        <div>
          <strong>Greater Phoenix</strong>
          <span>
            {sites.length} selected{" "}
            {sites.length === 1 ? "location" : "locations"}
          </span>
        </div>
      </div>
      <div className="map-note">
        <Layers size={13} />
        {tileError
          ? "Map layer unavailable · site markers remain visible"
          : "Site locations · not a temperature heatmap"}
      </div>
      {!sites.length ? (
        <div className="map-empty">
          Select locations to build your comparison
        </div>
      ) : null}
    </section>
  );
}
