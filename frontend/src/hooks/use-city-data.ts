import { useQuery } from "@tanstack/react-query";

type CityData = Record<string, string[]>;

async function fetchCityData(): Promise<CityData> {
  const res = await fetch("/data/cities.json");
  if (!res.ok) throw new Error("Failed to load city data");
  return res.json() as Promise<CityData>;
}

export function useCityData() {
  return useQuery({
    queryKey: ["static", "cities"],
    queryFn: fetchCityData,
    staleTime: Infinity,
    gcTime: Infinity,
  });
}

export function useCountryOptions() {
  const { data } = useCityData();
  if (!data) return [];
  return Object.keys(data).sort();
}

export function useCitiesForCountry(country: string) {
  const { data } = useCityData();
  if (!data || !country) return [];
  return data[country] ?? [];
}
