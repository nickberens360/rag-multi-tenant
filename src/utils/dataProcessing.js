// --- Helper functions for processing code frequency data ---

function validateFrequencyData(frequencyData) {
  if (frequencyData && frequencyData.computing) {
    return { isValid: false, message: frequencyData.message };
  }
  if (frequencyData && frequencyData.error) {
    return { isValid: false, message: frequencyData.message };
  }
  if (!Array.isArray(frequencyData)) {
    return { isValid: false, message: 'Invalid data format received' };
  }
  if (frequencyData.length === 0) {
    return {
      isValid: false,
      message: 'No code frequency data available. This could be because the repository is new, private, or the GitHub API has not calculated the statistics yet.'
    };
  }
  return { isValid: true };
}

function calculateGraphScale(data) {
  let maxAddition = 0;
  let maxDeletion = 0;
  data.forEach(week => {
    maxAddition = Math.max(maxAddition, week[1]);
    maxDeletion = Math.max(maxDeletion, Math.abs(week[2]));
  });
  const maxValue = Math.max(maxAddition, maxDeletion);
  const graphHeight = 10;
  const scaleFactor = maxValue > 0 ? graphHeight / maxValue : 0;
  return { maxValue, scaleFactor };
}

function mapDataToWeeks(data, { maxValue, scaleFactor }) {
  return data.map(week => {
    const date = new Date(week[0] * 1000).toISOString().split('T')[0];
    const additions = week[1];
    const deletions = Math.abs(week[2]);
    const additionBars = maxValue > 0 ? Math.round(additions * scaleFactor) : 0;
    const deletionBars = maxValue > 0 ? Math.round(deletions * scaleFactor) : 0;
    return { date, additions, deletions, additionBars, deletionBars };
  });
}

// Process code frequency data for display
export function processCodeFrequencyData(frequencyData) {
  const validation = validateFrequencyData(frequencyData);
  if (!validation.isValid) {
    return { title: 'Code Frequency Data', weeks: [], note: validation.message, isVisible: true, noData: true };
  }

  const recentData = frequencyData.slice(-10);
  const scale = calculateGraphScale(recentData);
  const weeks = mapDataToWeeks(recentData, scale);

  return {
    title: 'Additions (+) / Deletions (-) - Last 10 weeks',
    weeks,
    note: 'Note: Graph is scaled to fit the terminal window',
    isVisible: true,
    noData: false
  };
}

// Process commit history data for display
export function processCommitHistory(commits) {
  if (commits && commits.error) {
    return {
      title: 'Git Commit History',
      commits: [],
      message: commits.message,
      isVisible: true,
      error: true
    };
  }

  if (!Array.isArray(commits)) {
    return {
      title: 'Git Commit History',
      commits: [],
      message: 'Invalid data format received',
      isVisible: true,
      error: true
    };
  }

  if (commits.length === 0) {
    return {
      title: 'Git Commit History',
      commits: [],
      message: 'No commit history available.',
      isVisible: true,
      error: true
    };
  }

  return {
    title: 'Git Commit History',
    commits: commits.map(commit => ({
      hash: commit.hash,
      message: commit.message,
      url: commit.url
    })),
    note: `Showing ${commits.length} most recent commits`,
    isVisible: true,
    error: false
  };
}
