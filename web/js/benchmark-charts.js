/**
 * Benchmark Charts Module
 * Handles all chart rendering for the Benchmark dashboard
 * Uses Chart.js via CDN
 */

// Ensure Chart.js is loaded
if (typeof Chart === 'undefined') {
  console.warn('Chart.js not loaded, charts may not render');
}

// Color palette for charts
const BM_COLORS = {
  primary: '#3b82f6',
  success: '#22c55e',
  warning: '#f59e0b',
  danger: '#ef4444',
  info: '#06b6d4',
  purple: '#a855f7',
  colors: ['#3b82f6', '#22c55e', '#f59e0b', '#a855f7', '#06b6d4', '#ec4899', '#14b8a6', '#f97316']
};

// Chart instances storage
const bmCharts = {};

/**
 * Initialize Chart.js defaults
 */
function bmInitCharts() {
  if (typeof Chart === 'undefined') return;
  
  Chart.defaults.color = '#a0aec0';
  Chart.defaults.borderColor = '#2d3748';
  Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
}

/**
 * Destroy existing chart
 */
function bmDestroyChart(canvasId) {
  if (bmCharts[canvasId]) {
    bmCharts[canvasId].destroy();
    delete bmCharts[canvasId];
  }
}

/**
 * Render Overall Score Radar Chart
 */
function bmRenderRadarChart(canvasId, data) {
  bmDestroyChart(canvasId);
  
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  
  bmCharts[canvasId] = new Chart(ctx, {
    type: 'radar',
    data: {
      labels: data.labels || ['准确性', '完整性', '速度', '一致性', '鲁棒性'],
      datasets: [{
        label: data.modelName || 'Model',
        data: data.values || [0, 0, 0, 0, 0],
        backgroundColor: 'rgba(59, 130, 246, 0.2)',
        borderColor: BM_COLORS.primary,
        borderWidth: 2,
        pointBackgroundColor: BM_COLORS.primary,
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: BM_COLORS.primary
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          angleLines: { color: '#2d3748' },
          grid: { color: '#2d3748' },
          pointLabels: { color: '#a0aec0', font: { size: 11 } },
          suggestedMin: 0,
          suggestedMax: 100
        }
      },
      plugins: {
        legend: { display: true, position: 'bottom', labels: { color: '#a0aec0' } }
      }
    }
  });
}

/**
 * Render Performance Line Chart
 */
function bmRenderLineChart(canvasId, data) {
  bmDestroyChart(canvasId);
  
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  
  const datasets = data.datasets || [];
  
  bmCharts[canvasId] = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.labels || [],
      datasets: datasets.map((ds, i) => ({
        label: ds.label || `Series ${i + 1}`,
        data: ds.data || [],
        borderColor: ds.color || BM_COLORS.colors[i % BM_COLORS.colors.length],
        backgroundColor: (ds.color || BM_COLORS.colors[i % BM_COLORS.colors.length]).replace(')', ', 0.1)').replace('rgb', 'rgba'),
        fill: true,
        tension: 0.3,
        pointRadius: 3,
        pointHoverRadius: 6
      }))
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false
      },
      scales: {
        x: {
          grid: { color: '#2d3748' },
          ticks: { color: '#718096' }
        },
        y: {
          grid: { color: '#2d3748' },
          ticks: { color: '#718096' },
          beginAtZero: true
        }
      },
      plugins: {
        legend: { display: true, position: 'bottom' },
        tooltip: { enabled: true }
      }
    }
  });
}

/**
 * Render Bar Chart (Horizontal)
 */
function bmRenderHorizontalBar(canvasId, data) {
  bmDestroyChart(canvasId);
  
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  
  bmCharts[canvasId] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.labels || [],
      datasets: [{
        label: data.label || 'Score',
        data: data.values || [],
        backgroundColor: data.colors || BM_COLORS.colors,
        borderColor: data.colors || BM_COLORS.colors,
        borderWidth: 1,
        borderRadius: 4
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: { color: '#2d3748' },
          ticks: { color: '#718096' },
          beginAtZero: true,
          max: 100
        },
        y: {
          grid: { display: false },
          ticks: { color: '#a0aec0' }
        }
      },
      plugins: {
        legend: { display: false }
      }
    }
  });
}

/**
 * Render Doughnut Chart
 */
function bmRenderDoughnut(canvasId, data) {
  bmDestroyChart(canvasId);
  
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  
  bmCharts[canvasId] = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: data.labels || ['成功', '失败', '进行中'],
      datasets: [{
        data: data.values || [0, 0, 0],
        backgroundColor: [BM_COLORS.success, BM_COLORS.danger, BM_COLORS.warning],
        borderColor: '#1a1f2e',
        borderWidth: 2
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '60%',
      plugins: {
        legend: { display: true, position: 'bottom', labels: { color: '#a0aec0', padding: 15 } }
      }
    }
  });
}

/**
 * Render Multi-Model Comparison Chart
 */
function bmRenderModelComparison(canvasId, data) {
  bmDestroyChart(canvasId);
  
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  
  const models = data.models || [];
  const metrics = data.metrics || ['准确率', '速度', '完整性'];
  
  const datasets = models.map((model, i) => ({
    label: model.name,
    data: model.scores || [0, 0, 0],
    backgroundColor: BM_COLORS.colors[i % BM_COLORS.colors.length],
    borderColor: BM_COLORS.colors[i % BM_COLORS.colors.length],
    borderWidth: 1,
    borderRadius: 4
  }));
  
  bmCharts[canvasId] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: metrics,
      datasets: datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#a0aec0' }
        },
        y: {
          grid: { color: '#2d3748' },
          ticks: { color: '#718096' },
          beginAtZero: true,
          max: 100
        }
      },
      plugins: {
        legend: { display: true, position: 'bottom', labels: { color: '#a0aec0' } }
      }
    }
  });
}

/**
 * Render Error Distribution Chart
 */
function bmRenderErrorChart(canvasId, data) {
  bmDestroyChart(canvasId);
  
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  
  bmCharts[canvasId] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: data.labels || ['超时', 'API错误', '数据缺失', '格式错误', '其他'],
      datasets: [{
        label: '错误次数',
        data: data.values || [0, 0, 0, 0, 0],
        backgroundColor: BM_COLORS.danger,
        borderColor: BM_COLORS.danger,
        borderWidth: 1,
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#a0aec0' }
        },
        y: {
          grid: { color: '#2d3748' },
          ticks: { color: '#718096' },
          beginAtZero: true
        }
      },
      plugins: {
        legend: { display: false }
      }
    }
  });
}

/**
 * Render Execution Timeline (Gantt-style)
 */
function bmRenderTimeline(canvasId, data) {
  bmDestroyChart(canvasId);
  
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  
  const tasks = data.tasks || [];
  
  bmCharts[canvasId] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: tasks.map(t => t.name),
      datasets: [{
        label: '执行时间',
        data: tasks.map(t => t.duration || 0),
        backgroundColor: tasks.map(t => {
          if (t.status === 'failed') return BM_COLORS.danger;
          if (t.status === 'running') return BM_COLORS.warning;
          return BM_COLORS.success;
        }),
        borderColor: 'transparent',
        borderWidth: 0,
        borderRadius: 4
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          grid: { color: '#2d3748' },
          ticks: { color: '#718096', callback: v => v + 's' },
          beginAtZero: true
        },
        y: {
          grid: { display: false },
          ticks: { color: '#a0aec0', font: { size: 11 } }
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.raw}s`
          }
        }
      }
    }
  });
}

/**
 * Update all charts with new data
 */
function bmUpdateCharts(chartData) {
  if (chartData.radar) bmRenderRadarChart('bmRadarChart', chartData.radar);
  if (chartData.line) bmRenderLineChart('bmLineChart', chartData.line);
  if (chartData.horizontalBar) bmRenderHorizontalBar('bmHorizontalBar', chartData.horizontalBar);
  if (chartData.doughnut) bmRenderDoughnut('bmDoughnutChart', chartData.doughnut);
  if (chartData.comparison) bmRenderModelComparison('bmComparisonChart', chartData.comparison);
  if (chartData.errors) bmRenderErrorChart('bmErrorChart', chartData.errors);
  if (chartData.timeline) bmRenderTimeline('bmTimelineChart', chartData.timeline);
}

/**
 * Generate mock benchmark data for demonstration
 */
function bmGenerateMockData() {
  return {
    summary: {
      totalTasks: 45,
      completed: 38,
      failed: 5,
      running: 2,
      overallScore: 87.3,
      avgDuration: 12.5,
      successRate: 84.4
    },
    radar: {
      modelName: 'MiniMax-M2.7',
      labels: ['准确性', '完整性', '速度', '一致性', '鲁棒性'],
      values: [92, 85, 88, 90, 82]
    },
    line: {
      labels: ['Run 1', 'Run 2', 'Run 3', 'Run 4', 'Run 5', 'Run 6'],
      datasets: [
        { label: '准确率', data: [85, 87, 86, 89, 91, 92], color: BM_COLORS.primary },
        { label: '完整性', data: [78, 80, 82, 81, 84, 85], color: BM_COLORS.success },
        { label: '速度指数', data: [90, 88, 87, 89, 86, 88], color: BM_COLORS.warning }
      ]
    },
    horizontalBar: {
      labels: ['天文问答', '星图识别', '光变分析', '坐标转换', '光谱处理'],
      values: [95, 82, 78, 91, 88],
      colors: [BM_COLORS.success, BM_COLORS.primary, BM_COLORS.warning, BM_COLORS.primary, BM_COLORS.primary]
    },
    doughnut: {
      labels: ['成功', '失败', '进行中'],
      values: [38, 5, 2]
    },
    comparison: {
      models: [
        { name: 'MiniMax-M2.7', scores: [92, 88, 85] },
        { name: 'Qwen-Max', scores: [89, 85, 88] },
        { name: 'GPT-4o', scores: [94, 82, 79] },
        { name: 'Claude-3', scores: [91, 90, 86] }
      ],
      metrics: ['准确率', '速度', '完整性']
    },
    errors: {
      labels: ['超时', 'API错误', '数据缺失', '格式错误', '其他'],
      values: [12, 5, 8, 3, 2]
    },
    timeline: {
      tasks: [
        { name: '初始化', duration: 1.2, status: 'completed' },
        { name: '数据加载', duration: 3.5, status: 'completed' },
        { name: '模型推理', duration: 8.2, status: 'completed' },
        { name: '结果验证', duration: 2.1, status: 'failed' },
        { name: '报告生成', duration: 1.8, status: 'running' }
      ]
    },
    tasks: [
      { id: 't1', name: 'M31星系查询', status: 'completed', score: 95, difficulty: 'P1' },
      { id: 't2', name: '光谱类型识别', status: 'completed', score: 88, difficulty: 'P1' },
      { id: 't3', name: '光变曲线拟合', status: 'failed', score: 0, difficulty: 'P2' },
      { id: 't4', name: '坐标转换计算', status: 'completed', score: 91, difficulty: 'P0' },
      { id: 't5', name: '多源数据融合', status: 'running', score: null, difficulty: 'P2' }
    ],
    history: [
      { date: '2026-05-18', score: 85.2, tasks: 40, success: 34 },
      { date: '2026-05-17', score: 82.7, tasks: 38, success: 31 },
      { date: '2026-05-16', score: 88.1, tasks: 42, success: 37 },
      { date: '2026-05-15', score: 79.3, tasks: 35, success: 28 },
      { date: '2026-05-14', score: 86.5, tasks: 41, success: 35 }
    ]
  };
}

/**
 * Export benchmark data to JSON
 */
function bmExportJSON(data) {
  const jsonStr = JSON.stringify(data, null, 2);
  const blob = new Blob([jsonStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `benchmark_export_${new Date().toISOString().slice(0,10)}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Export benchmark data to CSV
 */
function bmExportCSV(data) {
  if (!data.tasks && !data.history) {
    alert('No data available to export');
    return;
  }
  
  let csv = '';
  
  // Tasks export
  if (data.tasks && data.tasks.length > 0) {
    csv += 'Task ID,Task Name,Status,Score,Difficulty\n';
    data.tasks.forEach(t => {
      csv += `${t.id},"${t.name}",${t.status},${t.score || ''},${t.difficulty}\n`;
    });
    csv += '\n';
  }
  
  // History export
  if (data.history && data.history.length > 0) {
    csv += 'Date,Overall Score,Total Tasks,Successful Tasks\n';
    data.history.forEach(h => {
      csv += `${h.date},${h.score},${h.tasks},${h.success}\n`;
    });
  }
  
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `benchmark_export_${new Date().toISOString().slice(0,10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// Initialize charts when DOM is ready
document.addEventListener('DOMContentLoaded', bmInitCharts);
