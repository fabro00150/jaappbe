$(function () {
  const payload = window.chartData;

  var options_sales_overview = {
    series: payload.series,
    chart: {
      type: "bar",
      height: 275,
      toolbar: { show: false },
      foreColor: "#adb0bb",
      fontFamily: "inherit",
    },
    grid: {
      show: false,
      borderColor: "transparent",
      padding: { left: 0, right: 0, bottom: 0 },
    },
    plotOptions: {
      bar: {
        horizontal: false,
        columnWidth: "25%",
        endingShape: "rounded",
        borderRadius: 5,
      },
    },
    colors: ["var(--bs-primary)", "var(--bs-secondary)"],
    dataLabels: { enabled: false },
    yaxis: { show: true },
    stroke: {
      show: true,
      width: 5,
      lineCap: "butt",
      colors: ["transparent"],
    },
    xaxis: {
      type: "category",
      categories: payload.labels,
      axisBorder: { show: false },
    },
    fill: { opacity: 1 },
    tooltip: { theme: "dark" },
    legend: { show: true },
  };

  var chart_column_basic = new ApexCharts(
    document.querySelector("#sales-overview"),
    options_sales_overview
  );
  chart_column_basic.render();
});
