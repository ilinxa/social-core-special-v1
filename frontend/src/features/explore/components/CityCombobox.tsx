"use client";

import { useEffect, useState } from "react";
import { Check, ChevronsUpDown } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";
import { useCitiesForCountry } from "@/features/explore/hooks/use-city-data";

interface CityComboboxProps {
  id?: string;
  country: string;
  value: string;
  onChange: (value: string) => void;
}

export function CityCombobox({ id, country, value, onChange }: CityComboboxProps) {
  const [open, setOpen] = useState(false);
  const cities = useCitiesForCountry(country);

  // Clear city if country changes and city is no longer valid
  useEffect(() => {
    if (value && cities.length > 0 && !cities.includes(value)) {
      onChange("");
    }
  }, [cities, value, onChange]);

  const disabled = !country;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          id={id}
          variant="outline"
          role="combobox"
          aria-expanded={open}
          disabled={disabled}
          className="h-8 w-full justify-between text-xs font-normal"
        >
          <span className="truncate">
            {value || (disabled ? "Select country first" : "All cities")}
          </span>
          <ChevronsUpDown className="ml-1 h-3 w-3 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
        <Command>
          <CommandInput placeholder="Search city..." className="h-8 text-xs" />
          <CommandList>
            <CommandEmpty>No city found.</CommandEmpty>
            <CommandGroup>
              <CommandItem
                value="all-cities"
                onSelect={() => {
                  onChange("");
                  setOpen(false);
                }}
              >
                <Check
                  className={cn(
                    "mr-2 h-3.5 w-3.5 shrink-0",
                    !value ? "opacity-100" : "opacity-0",
                  )}
                />
                All cities
              </CommandItem>
              {cities.map((city) => (
                <CommandItem
                  key={city}
                  value={city}
                  onSelect={() => {
                    onChange(city);
                    setOpen(false);
                  }}
                >
                  <Check
                    className={cn(
                      "mr-2 h-3.5 w-3.5 shrink-0",
                      value === city ? "opacity-100" : "opacity-0",
                    )}
                  />
                  {city}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
