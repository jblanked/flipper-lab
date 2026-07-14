export interface Category {
  id: number;
  name: string;
  my_order: number;
}

export interface App {
  id: number;
  author: string;
  category: string;        // serialized as name string
  category_id: number;
  changelog: string;
  description: string;
  fap_id: string;
  icon: string;            // absolute URL or ""
  name: string;
  screenshots: string[];
  short_description: string;
  version: string;
}
