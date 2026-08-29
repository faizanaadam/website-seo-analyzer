import React, { useState } from 'react';
import { StyleSheet, View, StatusBar } from 'react-native';
import { THEME } from './src/constants/theme';
import { AppState, AnalysisReportData } from './src/types/analysis';
import { MOCK_ANALYSIS_DATA } from './src/data/mockAnalysis';
import { InputState } from './src/components/InputState';
import { LoadingState } from './src/components/LoadingState';
import { ResultsState } from './src/components/ResultsState';
import { ErrorState } from './src/components/ErrorState';

export default function App() {
  const [appState, setAppState] = useState<AppState>('input');
  const [currentUrl, setCurrentUrl] = useState<string>('https://bright-smile-clinic.com');
  const [simulateError, setSimulateError] = useState<boolean>(false);
  const [reportData, setReportData] = useState<AnalysisReportData>(MOCK_ANALYSIS_DATA);

  // Trigger analysis flow
  const handleStartAnalysis = (url: string, shouldError: boolean = false) => {
    setCurrentUrl(url);
    const triggerError = shouldError || url.toLowerCase().includes('error');
    setSimulateError(triggerError);

    // Update mock target URL to match user input for realistic preview
    setReportData({
      ...MOCK_ANALYSIS_DATA,
      targetUrl: url.startsWith('http') ? url : `https://${url}`,
      businessName: url.includes('apex') ? 'Apex Auto Repair' : MOCK_ANALYSIS_DATA.businessName,
    });

    setAppState('loading');
  };

  // Loading completed successfully
  const handleLoadingComplete = () => {
    setAppState('results');
  };

  // Loading encountered error
  const handleLoadingError = () => {
    setAppState('error');
  };

  // Reset back to input state
  const handleReset = () => {
    setAppState('input');
    setSimulateError(false);
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={THEME.colors.background} />

      {appState === 'input' && <InputState onStartAnalysis={handleStartAnalysis} />}

      {appState === 'loading' && (
        <LoadingState
          targetUrl={currentUrl}
          shouldSimulateError={simulateError}
          onComplete={handleLoadingComplete}
          onError={handleLoadingError}
        />
      )}

      {appState === 'results' && <ResultsState data={reportData} onReset={handleReset} />}

      {appState === 'error' && (
        <ErrorState
          targetUrl={currentUrl}
          onRetry={() => handleStartAnalysis(currentUrl, false)}
          onBack={handleReset}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: THEME.colors.background,
  },
});
