import React, { useEffect, useState, useRef} from "react";
import Plot from 'react-plotly.js';

const App = () => {
  const [odData, setOdData] = useState([]);
  const [incTempData, setIncTempData] = useState([]);
  const [isRunning, setIsRunning] = useState(false);
  const [startTime, setStartTime] = useState(null);
  const isRunningRef = useRef(isRunning);

  useEffect(() => {
    isRunningRef.current = isRunning;
  }, [isRunning]);

  useEffect(() => {
    
    const fetchData = async () => {
      if (isRunningRef.current) {
        const response = await fetch("http://localhost:8000/api/data?command=current_state");
        const { status, data } = await response.json();
  
        if (status === "ok") {
          setOdData([...odData, data.od]);
          setIncTempData([...incTempData, data.inc_temp]);
        }
      }
      
    };

    fetchExperimentInfo();
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

  const fetchExperimentInfo = async () => {
    const response = await fetch('http://localhost:8000/api/data?command=experiment_info');
    const { status, data } = await response.json();
    if (status === "ok") {
      setIsRunning(data.is_running);
      setStartTime(data.start_time);
    }  else {
      // Replace with your preferred method of showing an error
      alert('Error fetcging experiment info');
    }
  };

  const newExperiment = async () => {
    const confirmResult = window.confirm("Are you sure you want to start a new experiment? This will erase all existing experiment data.");
    if (confirmResult) {
      const response = await fetch('http://localhost:8000/api/data?command=new_experiment');
      const { status } = await response.json();
      
      if (status === 'ok') {
        //Fetch new experiment info
        await fetchExperimentInfo();
        // Clear the plots
        setOdData([]);
        setIncTempData([]);
      } else {
        alert('Error starting a new experiment');
      }
    }
  };
  
  const startExperiment = async () => {
    const response = await fetch('http://localhost:8000/api/data?command=start');
    const { status } = await response.json();
    
    if (status === 'ok') {
      setIsRunning(true);
    } else {
      // Replace with your preferred method of showing an error
      alert('Error starting the experiment');
    }
  };
  
  const stopExperiment = async () => {
    const response = await fetch('http://localhost:8000/api/data?command=stop');
    const { status } = await response.json();
    
    if (status === 'ok') {
      setIsRunning(false);
    } else {
      // Replace with your preferred method of showing an error
      alert('Error stopping the experiment');
    }
  };

  const downloadData = async () => {
    const response = await fetch("http://localhost:8000/api/data?command=load_state_history");
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'data.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const formatDate = (epoch) => {
    if (epoch === null) return 'N/A';
    const date = new Date(epoch * 1000);
    return date.toLocaleString();
  };

  return (
    <>
      <div>
        Experiment Start Date: {formatDate(startTime)}
      </div>
      <button disabled={isRunning} onClick={newExperiment}>New Experiment</button>
      <button onClick={startExperiment} disabled={isRunning === null ? true : isRunning}>Start</button>
      <button onClick={stopExperiment} disabled={isRunning === null ? true : !isRunning}>Stop</button>
      <button onClick={downloadData} disabled={isRunning || startTime === null}>Download Data</button>
      <Plot data={odPlotData} layout={{ title: 'OD Plot' }} />
      <Plot data={incTempPlotData} layout={{ title: 'Inc Temp Plot' }} />
    </>
  );
};

export default App;

