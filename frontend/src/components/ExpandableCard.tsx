import React, { useState } from 'react';
import { StyleSheet, Text, View, TouchableOpacity } from 'react-native';
import { THEME } from '../constants/theme';
import { TechnicalCheckItem } from '../types/analysis';
import { StatusBadge } from './StatusBadge';

interface ExpandableCardProps {
  check: TechnicalCheckItem;
  initiallyExpanded?: boolean;
}

export const ExpandableCard: React.FC<ExpandableCardProps> = ({
  check,
  initiallyExpanded = false,
}) => {
  const [expanded, setExpanded] = useState<boolean>(initiallyExpanded);

  return (
    <View style={styles.card}>
      <TouchableOpacity
        style={styles.header}
        onPress={() => setExpanded(!expanded)}
        activeOpacity={0.7}
      >
        <View style={styles.headerTop}>
          <Text style={styles.title}>{check.name}</Text>
          <View style={styles.headerRight}>
            <StatusBadge type="check" status={check.status} size="sm" />
            <Text style={styles.chevron}>{expanded ? '▾' : '›'}</Text>
          </View>
        </View>

        <Text style={styles.summaryText}>{check.summary}</Text>
      </TouchableOpacity>

      {expanded && (
        <View style={styles.expandedContent}>
          <View style={styles.detailSection}>
            <Text style={styles.detailLabel}>WHY IT MATTERS</Text>
            <Text style={styles.detailBody}>{check.whyItMatters}</Text>
          </View>

          {check.evidence ? (
            <View style={styles.detailSection}>
              <Text style={styles.detailLabel}>EVIDENCE FOUND</Text>
              <View style={styles.codeSnippet}>
                <Text style={styles.codeText}>{check.evidence}</Text>
              </View>
            </View>
          ) : null}

          {check.suggestedAction ? (
            <View style={styles.detailSection}>
              <Text style={styles.detailLabel}>SUGGESTED ACTION</Text>
              <Text style={styles.actionBody}>{check.suggestedAction}</Text>
            </View>
          ) : null}
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: THEME.colors.surface,
    borderRadius: THEME.borderRadius.md,
    borderWidth: 1,
    borderColor: THEME.colors.border,
    marginBottom: THEME.spacing.sm,
    overflow: 'hidden',
  },
  header: {
    padding: THEME.spacing.md,
  },
  headerTop: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  title: {
    fontSize: 15,
    fontWeight: '700',
    color: THEME.colors.textPrimary,
    flex: 1,
    marginRight: 8,
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  chevron: {
    fontSize: 18,
    color: THEME.colors.textSecondary,
    fontWeight: '700',
    width: 14,
    textAlign: 'center',
  },
  summaryText: {
    fontSize: 13,
    color: THEME.colors.textSecondary,
    lineHeight: 18,
  },
  expandedContent: {
    paddingHorizontal: THEME.spacing.md,
    paddingBottom: THEME.spacing.md,
    paddingTop: THEME.spacing.xs,
    borderTopWidth: 1,
    borderTopColor: THEME.colors.border,
    backgroundColor: 'rgba(15, 23, 42, 0.4)',
  },
  detailSection: {
    marginTop: 10,
  },
  detailLabel: {
    fontSize: 10,
    fontWeight: '800',
    color: THEME.colors.textMuted,
    letterSpacing: 0.8,
    marginBottom: 4,
  },
  detailBody: {
    fontSize: 13,
    color: THEME.colors.textSecondary,
    lineHeight: 18,
  },
  codeSnippet: {
    backgroundColor: THEME.colors.background,
    borderRadius: THEME.borderRadius.sm,
    padding: 10,
    borderWidth: 1,
    borderColor: THEME.colors.border,
    marginTop: 2,
  },
  codeText: {
    fontSize: 12,
    color: THEME.colors.primaryLight,
    fontFamily: 'monospace',
    lineHeight: 16,
  },
  actionBody: {
    fontSize: 13,
    color: THEME.colors.textPrimary,
    fontWeight: '600',
    lineHeight: 18,
  },
});
