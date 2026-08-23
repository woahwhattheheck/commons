import { createFileRoute } from "@tanstack/react-router";
import { DoorApp } from "@/components/door-app";

export const Route = createFileRoute("/")({ component: Home });

function Home() {
  return <DoorApp />;
}
