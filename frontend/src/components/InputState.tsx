import React, { useState } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { THEME } from '../constants/theme';

interface InputStateProps {
  onStartAnalysis: (url: string, shouldSimulateError?: boolean) => void;
}

export const InputState: React.FC<InputStateProps> = ({ onStartAnalysis }) => {
  const [url, setUrl] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleRun = () => {
    const trimmed = url.trim();
    if (!trimmed) {
      setErrorMessage('Please enter a website address.');
      return;
    }

    if (!trimmed.includes('.') || trimmed.length < 4) {
      setErrorMessage('Please enter a valid website domain (e.g. example.com).');
      return;
    }

    setErrorMessage(null);
    onStartAnalysis(trimmed);
  };

  const handleSimulateError = () => {
    onStartAnalysis('https://invalid-nonexistent-domain.xyz', true);
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      {/* Header Badge */}
      <View style={styles.header}>
        <View style={styles.pillBadge}>
          <Text style={styles.pillText}>AUTOMATED VISIBILITY AUDIT</Text>
        </View>
        <Text style={styles.title}>Website SEO & Visibility Analyser</Text>
        <Text style={styles.subtitle}>
          Understand how your website performs and discover what to improve.
        </Text>
      </View>

      {/* Input Card */}
      <View style={styles.card}>
        <Text style={styles.inputLabel}>Enter website address</Text>
        <View style={styles.inputWrapper}>
          <TextInput
            style={styles.input}
            value={url}
            onChangeText={(text) => {
              setUrl(text);
              if (errorMessage) setErrorMessage(null);
            }}
            placeholder="https://yourwebsite.com"
            placeholderTextColor={THEME.colors.textMuted}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="url"
            returnKeyType="go"
            onSubmitEditing={handleRun}
          />
        </View>

        {errorMessage ? <Text style={styles.errorText}>⚠ {errorMessage}</Text> : null}

        {/* Quick Example Chips */}
        <View style={styles.chipContainer}>
          <Text style={styles.chipHeader}>Try sample websites:</Text>
          <View style={styles.chipRow}>
            <TouchableOpacity
              style={styles.chip}
              onPress={() => {
                setUrl('https://www.tajhotels.com');
                if (errorMessage) setErrorMessage(null);
              }}
              activeOpacity={0.7}
            >
              <Text style={styles.chipText}>tajhotels.com</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.chip}
              onPress={() => {
                setUrl('https://example.com');
                if (errorMessage) setErrorMessage(null);
              }}
              activeOpacity={0.7}
            >
              <Text style={styles.chipText}>example.com</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.chip}
              onPress={() => {
                setUrl('https://bright-smile-clinic.com');
                if (errorMessage) setErrorMessage(null);
              }}
              activeOpacity={0.7}
            >
              <Text style={styles.chipText}>bright-smile-clinic.com</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Primary CTA */}
        <TouchableOpacity style={styles.primaryButton} onPress={handleRun} activeOpacity={0.85}>
          <Text style={styles.primaryButtonText}>Analyse Website</Text>
        </TouchableOpacity>

        {/* Explanation */}
        <Text style={styles.explanationText}>
          We'll check your website's SEO, content, customer targeting and local visibility.
        </Text>
      </View>

      {/* Test Error State Trigger */}
      <View style={styles.debugBox}>
        <Text style={styles.debugLabel}>DEVELOPMENT PREVIEW CONTROLS</Text>
        <TouchableOpacity
          style={styles.debugButton}
          onPress={handleSimulateError}
          activeOpacity={0.7}
        >
          <Text style={styles.debugButtonText}>⚡ Test Error State Screen</Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: THEME.spacing.lg,
  },
  header: {
    marginBottom: THEME.spacing.xl,
  },
  pillBadge: {
    backgroundColor: 'rgba(2, 132, 199, 0.15)',
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: THEME.borderRadius.full,
    borderWidth: 1,
    borderColor: THEME.colors.primary,
    marginBottom: THEME.spacing.sm,
  },
  pillText: {
    fontSize: 11,
    fontWeight: '800',
    color: THEME.colors.primaryLight,
    letterSpacing: 0.8,
  },
  title: {
    fontSize: 28,
    fontWeight: '800',
    color: THEME.colors.textPrimary,
    lineHeight: 34,
  },
  subtitle: {
    fontSize: 15,
    color: THEME.colors.textSecondary,
    marginTop: THEME.spacing.sm,
    lineHeight: 22,
  },
  card: {
    backgroundColor: THEME.colors.surface,
    borderRadius: THEME.borderRadius.lg,
    padding: THEME.spacing.lg,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  inputLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: THEME.colors.textSecondary,
    marginBottom: THEME.spacing.xs,
  },
  inputWrapper: {
    backgroundColor: THEME.colors.background,
    borderRadius: THEME.borderRadius.md,
    borderWidth: 1,
    borderColor: THEME.colors.border,
    paddingHorizontal: THEME.spacing.md,
    paddingVertical: Platform.OS === 'ios' ? 14 : 10,
    marginBottom: THEME.spacing.xs,
  },
  input: {
    fontSize: 16,
    color: THEME.colors.textPrimary,
  },
  errorText: {
    fontSize: 12,
    color: THEME.colors.fail,
    marginTop: 4,
    fontWeight: '600',
  },
  chipContainer: {
    marginTop: THEME.spacing.md,
    marginBottom: THEME.spacing.lg,
  },
  chipHeader: {
    fontSize: 12,
    color: THEME.colors.textMuted,
    marginBottom: 6,
  },
  chipRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  chip: {
    backgroundColor: THEME.colors.surfaceLight,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: THEME.borderRadius.sm,
    borderWidth: 1,
    borderColor: THEME.colors.borderLight,
  },
  chipText: {
    fontSize: 12,
    color: THEME.colors.primaryLight,
    fontWeight: '500',
  },
  primaryButton: {
    backgroundColor: THEME.colors.primary,
    borderRadius: THEME.borderRadius.md,
    paddingVertical: 15,
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
  explanationText: {
    fontSize: 12,
    color: THEME.colors.textMuted,
    textAlign: 'center',
    marginTop: THEME.spacing.md,
    lineHeight: 16,
  },
  debugBox: {
    marginTop: THEME.spacing.xl,
    padding: THEME.spacing.md,
    backgroundColor: 'rgba(30, 41, 59, 0.5)',
    borderRadius: THEME.borderRadius.md,
    borderWidth: 1,
    borderColor: THEME.colors.border,
    borderStyle: 'dashed',
  },
  debugLabel: {
    fontSize: 10,
    fontWeight: '800',
    color: THEME.colors.textMuted,
    letterSpacing: 0.8,
    marginBottom: 8,
    textAlign: 'center',
  },
  debugButton: {
    backgroundColor: THEME.colors.surfaceLight,
    paddingVertical: 8,
    borderRadius: THEME.borderRadius.sm,
    alignItems: 'center',
  },
  debugButtonText: {
    fontSize: 12,
    color: THEME.colors.textSecondary,
    fontWeight: '600',
  },
});
