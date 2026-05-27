import { useCallback, useEffect, useRef, useState } from "react";
import { getCPBite, getMyProblems, getRandomTopic } from "../api/client";

const TIMEOUT_MS = 60_000;

export function useRefresher() {
  const [refresherDataByMode, setRefresherDataByMode] = useState({
    random: null,
    myproblems: null,
    cpbites: null,
  });
  const [loadingByMode, setLoadingByMode] = useState({
    random: false,
    myproblems: false,
    cpbites: false,
  });
  const [errorByMode, setErrorByMode] = useState({
    random: "",
    myproblems: "",
    cpbites: "",
  });
  const [fetchCount, setFetchCount] = useState(0);
  const controllersRef = useRef({});

  // Abort all in-flight requests on unmount
  useEffect(() => {
    return () => {
      Object.values(controllersRef.current).forEach((c) => c.abort());
    };
  }, []);

  const fetchRefresher = useCallback(async (mode) => {
    // Abort any existing in-flight request for this specific mode
    controllersRef.current[mode]?.abort();

    const controller = new AbortController();
    controllersRef.current[mode] = controller;

    let timedOut = false;
    const timeoutId = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, TIMEOUT_MS);

    setLoadingByMode((prev) => ({ ...prev, [mode]: true }));
    setErrorByMode((prev) => ({ ...prev, [mode]: "" }));

    try {
      let data;
      const opts = { signal: controller.signal };
      if (mode === "random") data = await getRandomTopic(opts);
      if (mode === "myproblems") data = await getMyProblems(1, opts);
      if (mode === "cpbites") data = await getCPBite(opts);
      setRefresherDataByMode((prev) => ({ ...prev, [mode]: data }));
      setFetchCount((c) => c + 1);
    } catch (err) {
      if (err.name === "AbortError") {
        if (timedOut) {
          setErrorByMode((prev) => ({
            ...prev,
            [mode]: "Request timed out — the LLM might be overloaded. Try again.",
          }));
          setRefresherDataByMode((prev) => ({ ...prev, [mode]: null }));
        }
        // Non-timeout abort (superseded request or unmount) — silently ignore
        return;
      }
      setErrorByMode((prev) => ({
        ...prev,
        [mode]: err.message || "Something went wrong",
      }));
      setRefresherDataByMode((prev) => ({ ...prev, [mode]: null }));
    } finally {
      clearTimeout(timeoutId);
      // Only clear loading if this is still the active controller for this mode
      // (avoids a superseded request prematurely clearing a newer request's loading state)
      if (controllersRef.current[mode] === controller) {
        setLoadingByMode((prev) => ({ ...prev, [mode]: false }));
      }
    }
  }, []);

  return { refresherDataByMode, loadingByMode, errorByMode, fetchRefresher, fetchCount };
}
