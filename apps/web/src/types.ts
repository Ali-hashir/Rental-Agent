export interface ListingCard {
  unitId: string;
  propertyId: string;
  propertyName: string;
  propertyCity: string;
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
  availableFrom: string | null;
}

export interface TimeSlot {
  start: string;
  end: string;
}
