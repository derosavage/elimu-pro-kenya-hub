import { createFileRoute } from "@tanstack/react-router";
import { ElimuProLanding } from "@/components/elimu-pro-landing";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Elimu Pro — Smarter School Management for Kenya" },
      { name: "description", content: "Run admissions, CBC reporting, M-Pesa fees, attendance and parent communication in one platform built for Kenyan schools." },
      { property: "og:title", content: "Elimu Pro — Smarter School Management for Kenya" },
      { property: "og:description", content: "One connected platform for every role in your school, built for Kenya." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: ElimuProLanding,
});
