import { Route, Routes } from "react-router-dom";

import Home from "@/routes/Home";
import Diagnose from "@/routes/Diagnose";
import Compare from "@/routes/Compare";
import Evidence from "@/routes/Evidence";
import Regulatory from "@/routes/Regulatory";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/diagnose" element={<Diagnose />} />
      <Route path="/compare" element={<Compare />} />
      <Route path="/evidence" element={<Evidence />} />
      <Route path="/regulatory" element={<Regulatory />} />
    </Routes>
  );
}
