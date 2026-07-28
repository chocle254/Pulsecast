'use client';

import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface ForecastPoint {
  week: number;
  vci3m: number;
  lower: number;
  upper: number;
}

interface HistoricalPoint {
  month: string;
  vci3m: number | null;
  spi: number | null;
  phase: string;
}

interface ThresholdChartProps {
  historical: HistoricalPoint[];
  forecast: ForecastPoint[];
  crossingDate?: string | null;
  crossingPhase?: string | null;
  daysToCrossing?: number | null;
  height?: number;
}

export default function ThresholdChart({
  historical,
  forecast,
  crossingDate,
  crossingPhase,
  daysToCrossing,
  height = 360,
}: ThresholdChartProps) {
  const svgRef = useRef<SVGSVGElement | null>(null);

  useEffect(() => {
    if (!svgRef.current || (!historical.length && !forecast.length)) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const margin = { top: 30, right: 90, bottom: 40, left: 50 };
    const containerWidth = svgRef.current.clientWidth || 700;
    const width = containerWidth - margin.left - margin.right;
    const chartHeight = height - margin.top - margin.bottom;

    const g = svg
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Prepare time series points
    const validHistorical = historical.filter((d) => d.vci3m !== null);

    // Combine timeline
    const dataPoints: { label: string; vci3m: number; isForecast: boolean; lower?: number; upper?: number }[] = [];

    validHistorical.forEach((h) => {
      dataPoints.push({
        label: h.month,
        vci3m: h.vci3m!,
        isForecast: false,
      });
    });

    if (forecast.length && validHistorical.length) {
      const lastHist = validHistorical[validHistorical.length - 1];
      forecast.forEach((f) => {
        dataPoints.push({
          label: `W+${f.week}`,
          vci3m: f.vci3m,
          isForecast: true,
          lower: f.lower,
          upper: f.upper,
        });
      });
    }

    // Scales
    const xScale = d3
      .scalePoint<string>()
      .domain(dataPoints.map((d) => d.label))
      .range([0, width]);

    const yScale = d3.scaleLinear().domain([0, 80]).range([chartHeight, 0]);

    // Gridlines
    const yAxisGrid = d3.axisLeft(yScale).tickSize(-width).tickFormat(() => '').ticks(5);
    g.append('g')
      .attr('class', 'grid')
      .call(yAxisGrid)
      .selectAll('line')
      .attr('stroke', '#E2E5DC')
      .attr('stroke-dasharray', '3,3');

    // NDMA Thresholds
    const thresholds = [
      { name: 'Normal', value: 50, color: '#7A9B76' },
      { name: 'Alert', value: 35, color: '#C9A24B' },
      { name: 'Alarm', value: 20, color: '#B9713A' },
      { name: 'Emergency', value: 10, color: '#9B3B34' },
    ];

    thresholds.forEach((t) => {
      const yPos = yScale(t.value);
      if (yPos >= 0 && yPos <= chartHeight) {
        g.append('line')
          .attr('x1', 0)
          .attr('y1', yPos)
          .attr('x2', width)
          .attr('y2', yPos)
          .attr('stroke', t.color)
          .attr('stroke-width', 1.25)
          .attr('stroke-dasharray', '4,4')
          .attr('opacity', 0.7);

        g.append('text')
          .attr('x', width + 8)
          .attr('y', yPos + 4)
          .attr('fill', t.color)
          .attr('font-size', '11px')
          .attr('font-weight', '600')
          .attr('font-family', 'var(--font-mono)')
          .text(`${t.name} (${t.value})`);
      }
    });

    // Confidence Band Area for forecast
    const forecastPoints = dataPoints.filter((d) => d.isForecast && d.lower !== undefined);
    if (forecastPoints.length) {
      // Connect to last historical point
      const lastHistPoint = dataPoints.find((d, i) => !d.isForecast && dataPoints[i + 1]?.isForecast);
      const bandPoints = lastHistPoint
        ? [{ label: lastHistPoint.label, vci3m: lastHistPoint.vci3m, isForecast: true, lower: lastHistPoint.vci3m, upper: lastHistPoint.vci3m }, ...forecastPoints]
        : forecastPoints;

      const area = d3
        .area<{ label: string; lower?: number; upper?: number }>()
        .x((d) => xScale(d.label) || 0)
        .y0((d) => yScale(d.lower ?? 0))
        .y1((d) => yScale(d.upper ?? 0))
        .curve(d3.curveMonotoneX);

      g.append('path')
        .datum(bandPoints)
        .attr('fill', '#B9713A')
        .attr('opacity', 0.12)
        .attr('d', area);
    }

    // Historical Line
    const histData = dataPoints.filter((d) => !d.isForecast);
    const lineHist = d3
      .line<{ label: string; vci3m: number }>()
      .x((d) => xScale(d.label) || 0)
      .y((d) => yScale(d.vci3m))
      .curve(d3.curveMonotoneX);

    const histPath = g
      .append('path')
      .datum(histData)
      .attr('fill', 'none')
      .attr('stroke', '#232A2E')
      .attr('stroke-width', 2.5)
      .attr('d', lineHist);

    // Left-to-right draw animation
    const pathNode = histPath.node();
    if (pathNode) {
      const totalLength = pathNode.getTotalLength();
      histPath
        .attr('stroke-dasharray', `${totalLength} ${totalLength}`)
        .attr('stroke-dashoffset', totalLength)
        .transition()
        .duration(800)
        .ease(d3.easeCubicOut)
        .attr('stroke-dashoffset', 0);
    }

    // Forecast Line (Dashed)
    const lastHist = histData[histData.length - 1];
    const fcData = lastHist ? [lastHist, ...dataPoints.filter((d) => d.isForecast)] : dataPoints.filter((d) => d.isForecast);

    const lineForecast = d3
      .line<{ label: string; vci3m: number }>()
      .x((d) => xScale(d.label) || 0)
      .y((d) => yScale(d.vci3m))
      .curve(d3.curveMonotoneX);

    g.append('path')
      .datum(fcData)
      .attr('fill', 'none')
      .attr('stroke', '#B9713A')
      .attr('stroke-width', 2.5)
      .attr('stroke-dasharray', '6,4')
      .attr('d', lineForecast);

    // Data Circles
    histData.forEach((d) => {
      const cx = xScale(d.label) || 0;
      const cy = yScale(d.vci3m);
      g.append('circle')
        .attr('cx', cx)
        .attr('cy', cy)
        .attr('r', 4)
        .attr('fill', '#FFFFFF')
        .attr('stroke', '#232A2E')
        .attr('stroke-width', 2);
    });

    fcData.slice(1).forEach((d) => {
      const cx = xScale(d.label) || 0;
      const cy = yScale(d.vci3m);
      g.append('circle')
        .attr('cx', cx)
        .attr('cy', cy)
        .attr('r', 4)
        .attr('fill', '#FFFFFF')
        .attr('stroke', '#B9713A')
        .attr('stroke-width', 2);
    });

    // Crossing Callout Annotation
    if (crossingDate && daysToCrossing && fcData.length > 1) {
      const crossingPoint = fcData[Math.min(2, fcData.length - 1)];
      const cx = xScale(crossingPoint.label) || width * 0.75;
      const cy = yScale(crossingPoint.vci3m);

      // Pin / line
      g.append('line')
        .attr('x1', cx)
        .attr('y1', cy)
        .attr('x2', cx)
        .attr('y2', cy - 35)
        .attr('stroke', '#9B3B34')
        .attr('stroke-width', 1.5)
        .attr('stroke-dasharray', '2,2');

      // Callout box
      const calloutGroup = g.append('g').attr('transform', `translate(${cx - 55}, ${cy - 65})`);

      calloutGroup
        .append('rect')
        .attr('width', 110)
        .attr('height', 26)
        .attr('rx', 4)
        .attr('fill', '#9B3B34')
        .attr('box-shadow', '0 2px 4px rgba(0,0,0,0.1)');

      calloutGroup
        .append('text')
        .attr('x', 55)
        .attr('y', 17)
        .attr('fill', '#FFFFFF')
        .attr('text-anchor', 'middle')
        .attr('font-size', '11px')
        .attr('font-weight', '600')
        .attr('font-family', 'var(--font-mono)')
        .text(`Cross: ${crossingDate}`);
    }

    // Axes
    const xAxis = d3.axisBottom(xScale);
    g.append('g')
      .attr('transform', `translate(0,${chartHeight})`)
      .call(xAxis)
      .selectAll('text')
      .attr('font-family', 'var(--font-mono)')
      .attr('font-size', '11px')
      .attr('fill', '#5B6560');

    const yAxis = d3.axisLeft(yScale).ticks(5);
    g.append('g')
      .call(yAxis)
      .selectAll('text')
      .attr('font-family', 'var(--font-mono)')
      .attr('font-size', '11px')
      .attr('fill', '#5B6560');

    // Axis label
    g.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('y', -38)
      .attr('x', -chartHeight / 2)
      .attr('text-anchor', 'middle')
      .attr('font-size', '11px')
      .attr('font-family', 'var(--font-mono)')
      .attr('fill', '#5B6560')
      .text('VCI3M Index');

  }, [historical, forecast, crossingDate, crossingPhase, daysToCrossing, height]);

  return (
    <div className="w-full relative">
      <svg ref={svgRef} className="w-full" style={{ height }} />
    </div>
  );
}
