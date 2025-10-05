import {useEffect, useState} from "react";

export default function useMobile() {
  const [is, setIs] = useState(false);
  useEffect(() => {
    if (typeof window !== "undefined") {
      setIs(window.matchMedia("(pointer: coarse)").matches);
    }
  }, []);
  return is;
}