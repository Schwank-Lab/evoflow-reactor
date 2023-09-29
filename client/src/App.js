import React, { useEffect, useState } from "react";
import Plot from 'react-plotly.js';

const App = () => {
  const [odData, setOdData] = useState([]);
  const [incTempData, setIncTempData] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      const response = await fetch("http://localhost:8000/api/data?command=current_state");
      const { status, data } = await response.json();

      if (status === "ok") {
        setOdData([...odData, data.od]);
        setIncTempData([...incTempData, data.inc_temp]);
      }
    };

    const interval = setInterval(fetchData, 1000);
    return () => clearInterval(interval);
  }, [odData, incTempData]);

  const odPlotData = [
    {
      y: odData,
      type: 'scatter',
      mode: 'lines+markers'
    }
  ];

  const incTempPlotData = [
    {
      y: incTempData,
      type: 'scatter',
      mode: 'lines+markers'
    }
  ];

  return (
    <>
      <Plot data={odPlotData} layout={{ title: 'OD Plot' }} />
      <Plot data={incTempPlotData} layout={{ title: 'Inc Temp Plot' }} />
    </>
  );
};

export default App;

