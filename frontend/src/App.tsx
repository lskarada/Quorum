import { Route, Routes } from "react-router-dom";

import Home from "@/routes/Home";
import Diagnose from "@/routes/Diagnose";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/diagnose" element={<Diagnose />} />
    </Routes>
  );
}
