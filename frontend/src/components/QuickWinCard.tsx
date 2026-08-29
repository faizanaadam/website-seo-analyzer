import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { THEME } from '../constants/theme';
import { QuickWinItem } from '../types/analysis';

interface QuickWinCardProps {
  item: QuickWinItem;
  index: number;
}

export const QuickWinCard: React.FC<QuickWinCardProps> = ({ item, index }) => {
  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <View style={styles.numberBadge}>
          <Text style={styles.numberText}>{index + 1}</Text>
        </View>
        <Text style={styles.title}>{item.title}</Text>
      </View>

      <Text style={styles.whyText}>{item.why}</Text>

      <View style={styles.metaRow}>
        <View style={styles.metaBadge}>
          <Text style={styles.metaLabel}>Impact: </Text>
          <Text
            style={[
              styles.metaValue,
              item.impact === 'High' && styles.impactHigh,
              item.impact === 'Medium' && styles.impactMedium,
            ]}
          >
            {item.impact}
          </Text>
        </View>

        <View style={styles.metaBadge}>
          <Text style={styles.metaLabel}>Time: </Text>
          <Text style={styles.metaValue}>{item.timeEstimate}</Text>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: THEME.colors.surface,
    borderRadius: THEME.borderRadius.md,
    padding: THEME.spacing.md,
    borderWidth: 1,
    borderColor: THEME.colors.border,
    marginBottom: THEME.spacing.sm,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: THEME.spacing.xs,
  },
  numberBadge: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: THEME.colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: THEME.spacing.sm,
  },
  numberText: {
    color: THEME.colors.textInverse,
    fontSize: 12,
    fontWeight: '800',
  },
  title: {
    flex: 1,
    fontSize: 15,
    fontWeight: '700',
    color: THEME.colors.textPrimary,
  },
  whyText: {
    fontSize: 13,
    color: THEME.colors.textSecondary,
    lineHeight: 18,
    marginTop: 4,
    marginBottom: 10,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  metaBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: THEME.colors.surfaceLight,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: THEME.borderRadius.sm,
  },
  metaLabel: {
    fontSize: 11,
    color: THEME.colors.textMuted,
    fontWeight: '500',
  },
  metaValue: {
    fontSize: 11,
    color: THEME.colors.textPrimary,
    fontWeight: '700',
  },
  impactHigh: {
    color: THEME.colors.pass,
  },
  impactMedium: {
    color: THEME.colors.primaryLight,
  },
});
