import { Route, Routes } from "react-router-dom";

import Home from "@/routes/Home";
import Diagnose from "@/routes/Diagnose";
import Compare from "@/routes/Compare";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/diagnose" element={<Diagnose />} />
      <Route path="/compare" element={<Compare />} />
    </Routes>
  );
}
