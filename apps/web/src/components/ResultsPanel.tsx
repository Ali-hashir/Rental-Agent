import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ListingCard } from "../types";

interface ResultsPanelProps {
  onBook: (listing: ListingCard) => void;
}

interface SearchListingsResponse {
  results: ListingPayload[];
  next_cursor: string | null;
}

interface ListingPayload {
  unit_id: string;
  property_id: string;
  property_name: string;
  property_city: string;
  title: string;
  rent: number;
  deposit: number | null;
  baths: number;
  beds: number;
  sqft: number | null;
  furnished: boolean;
  amenities: string[];
  address: string | null;
  images: string[];
  available_from: string | null;
}

const fetchListings = async (): Promise<ListingPayload[]> => {
  const response = await fetch("/api/agent/tool/search_listings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      filters: {},
      limit: 6
    })
  });

  if (!response.ok) {
    throw new Error("Failed to load listings");
  }
  const data = (await response.json()) as SearchListingsResponse;
  return data.results;
};

const formatRent = (amount: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "PKR", maximumFractionDigits: 0 }).format(amount);

export function ResultsPanel({ onBook }: ResultsPanelProps) {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["listings"],
    queryFn: fetchListings,
    staleTime: 5 * 60 * 1000
  });

  const listings: ListingCard[] = useMemo(() => {
    if (!data) {
      return [];
    }
    return data.map<ListingCard>((item) => ({
      unitId: item.unit_id,
      propertyId: item.property_id,
      propertyName: item.property_name,
      propertyCity: item.property_city,
      title: item.title,
      rent: item.rent,
      deposit: item.deposit,
      baths: item.baths,
      beds: item.beds,
      sqft: item.sqft,
      furnished: item.furnished,
      amenities: item.amenities,
      address: item.address,
      images: item.images,
      availableFrom: item.available_from
    }));
  }, [data]);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold">Results</h2>
        <button
          type="button"
          className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 transition hover:border-slate-500"
          onClick={() => refetch()}
        >
          Refresh
        </button>
      </div>

      {isLoading && (
        <p className="mt-2 text-sm text-slate-400">Fetching listings grounded in your database...</p>
      )}

      {isError && (
        <p className="mt-2 text-sm text-rose-400">Unable to load listings. Try refreshing in a moment.</p>
      )}

      {!isLoading && !isError && listings.length === 0 && (
        <p className="mt-2 text-sm text-slate-400">
          Listings will appear here once the agent shares results.
        </p>
      )}

      <div className="mt-4 space-y-4">
        {listings.map((listing) => (
          <div key={listing.unitId} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-base font-semibold text-white">{listing.title}</h3>
                <p className="text-xs text-slate-400">
                  {listing.propertyName}
                  {listing.propertyCity ? `, ${listing.propertyCity}` : ""}
                </p>
              </div>
              <span className="text-sm font-semibold text-emerald-400">{formatRent(listing.rent)}</span>
            </div>
            <p className="mt-2 text-xs text-slate-400">
              {listing.beds} bed | {listing.baths} bath | {listing.furnished ? "Furnished" : "Unfurnished"}
              {listing.availableFrom ? ` | Available ${new Date(listing.availableFrom).toLocaleDateString()}` : ""}
            </p>
            {listing.amenities.length > 0 && (
              <p className="mt-2 text-xs text-slate-500">
                Amenities: {listing.amenities.slice(0, 4).join(", ")}
                {listing.amenities.length > 4 ? "..." : ""}
              </p>
            )}
            <button
              className="mt-4 w-full rounded-full bg-emerald-500 px-4 py-2 text-sm font-medium text-black transition hover:bg-emerald-400"
              onClick={() => onBook(listing)}
            >
              Book viewing
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
