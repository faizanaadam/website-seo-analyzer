import React, { useState } from 'react';
import { StyleSheet, View, StatusBar } from 'react-native';
import { THEME } from './src/constants/theme';
import { AppState, AnalysisReportData } from './src/types/analysis';
import { InputState } from './src/components/InputState';
import { LoadingState } from './src/components/LoadingState';
import { ResultsState } from './src/components/ResultsState';
import { ErrorState } from './src/components/ErrorState';

export default function App() {
  const [appState, setAppState] = useState<AppState>('input');
  const [currentUrl, setCurrentUrl] = useState<string>('');
  const [simulateError, setSimulateError] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reportData, setReportData] = useState<AnalysisReportData | null>(null);

  // Trigger analysis flow
  const handleStartAnalysis = (url: string, shouldError: boolean = false) => {
    // 1. Immediately wipe previous report state to guarantee fresh data
    setReportData(null);
    setErrorMessage(null);
    setCurrentUrl(url);
    setSimulateError(shouldError);

    // 2. Transition to loading state
    setAppState('loading');
  };

  // Loading completed successfully with dynamic API data
  const handleLoadingComplete = (data: AnalysisReportData) => {
    setReportData(data);
    setAppState('results');
  };

  // Loading encountered error
  const handleLoadingError = (errorMsg: string) => {
    setErrorMessage(errorMsg);
    setAppState('error');
  };

  // Reset back to clean input state
  const handleReset = () => {
    setReportData(null);
    setErrorMessage(null);
    setSimulateError(false);
    setAppState('input');
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

      {appState === 'results' && reportData && (
        <ResultsState data={reportData} onReset={handleReset} />
      )}

      {appState === 'error' && (
        <ErrorState
          targetUrl={currentUrl}
          errorMessage={errorMessage || undefined}
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
