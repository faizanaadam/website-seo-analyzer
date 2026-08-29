import React from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  TouchableOpacity,
  SafeAreaView,
} from 'react-native';
import { THEME } from '../constants/theme';
import { AnalysisReportData } from '../types/analysis';
import { QuickWinCard } from './QuickWinCard';
import { ExpandableCard } from './ExpandableCard';
import { StatusBadge } from './StatusBadge';

interface ResultsStateProps {
  data: AnalysisReportData;
  onReset: () => void;
}

export const ResultsState: React.FC<ResultsStateProps> = ({ data, onReset }) => {
  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>
        {/* Top App Bar & Reset Button */}
        <View style={styles.topBar}>
          <View style={styles.siteHeader}>
            <Text style={styles.tagline}>WEBSITE VISIBILITY REPORT</Text>
            <Text style={styles.businessTitle}>{data.businessName}</Text>
            <Text style={styles.domainText}>{data.targetUrl}</Text>
          </View>
          <TouchableOpacity style={styles.newAuditBtn} onPress={onReset} activeOpacity={0.7}>
            <Text style={styles.newAuditText}>+ New Audit</Text>
          </TouchableOpacity>
        </View>

        {/* 1. Overall Health Summary Banner */}
        <View style={styles.summaryCard}>
          <Text style={styles.summaryHeadline}>Website Analysis Complete</Text>
          <Text style={styles.summaryNarrative}>{data.overall.summaryText}</Text>

          {/* Metric Badges */}
          <View style={styles.metricsRow}>
            <View style={[styles.metricBox, styles.metricPass]}>
              <Text style={styles.metricNumber}>{data.overall.passedCount}</Text>
              <Text style={styles.metricLabel}>Passed</Text>
            </View>

            <View style={[styles.metricBox, styles.metricWarn]}>
              <Text style={styles.metricNumber}>{data.overall.needsAttentionCount}</Text>
              <Text style={styles.metricLabel}>Need Attention</Text>
            </View>

            <View style={[styles.metricBox, styles.metricFail]}>
              <Text style={styles.metricNumber}>{data.overall.issuesCount}</Text>
              <Text style={styles.metricLabel}>Issues</Text>
            </View>
          </View>
        </View>

        {/* 2. Quick Wins Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>⚡ Quick Wins</Text>
            <Text style={styles.sectionSubtitle}>
              High-impact fixes you can complete in under an hour.
            </Text>
          </View>

          {data.quickWins.map((item, index) => (
            <QuickWinCard key={item.id} item={item} index={index} />
          ))}
        </View>

        {/* 3. Technical SEO Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>🛠 Technical SEO & Structure</Text>
            <Text style={styles.sectionSubtitle}>
              Foundational factors search engines use to discover and rank your site.
            </Text>
          </View>

          {data.technicalChecks.map((check) => (
            <ExpandableCard key={check.id} check={check} />
          ))}
        </View>

        {/* 4. Content & Website Structure */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>📄 Content & Website Structure</Text>
            <Text style={styles.sectionSubtitle}>
              Evaluating service depth, dedicated procedure pages, and conversion pathways.
            </Text>
          </View>

          <View style={styles.contentCard}>
            <Text style={styles.cardSectionLabel}>SERVICES DETECTED ON SITE</Text>
            <View style={styles.chipsRow}>
              {data.content.servicesDetected.map((service, i) => (
                <View key={i} style={styles.serviceChip}>
                  <Text style={styles.serviceChipText}>✓ {service}</Text>
                </View>
              ))}
            </View>

            <View style={styles.contentDivider} />

            <View style={styles.contentStatRow}>
              <Text style={styles.statLabel}>Dedicated Service Pages:</Text>
              <Text style={styles.statValue}>
                {data.content.dedicatedServicePages ? '✓ Yes (Individual procedures)' : '✕ No'}
              </Text>
            </View>

            <View style={styles.contentStatRow}>
              <Text style={styles.statLabel}>Homepage Word Count:</Text>
              <Text style={styles.statValue}>{data.content.homepageWordCount} words (Healthy)</Text>
            </View>

            <View style={styles.contentStatRow}>
              <Text style={styles.statLabel}>Call-to-Action Detected:</Text>
              <Text style={styles.statValue}>Online booking & Phone link</Text>
            </View>
          </View>
        </View>

        {/* 5. Ideal Customer Profile Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>🎯 Who Your Website Appears to Target</Text>
            <Text style={styles.sectionSubtitle}>
              Honest analysis distinguishing direct facts from inferred positioning.
            </Text>
          </View>

          <View style={styles.icpCard}>
            <Text style={styles.icpSummary}>{data.icp.summary}</Text>

            <View style={styles.icpList}>
              {data.icp.items.map((item, i) => (
                <View key={i} style={styles.icpItem}>
                  <View style={styles.icpItemHeader}>
                    <Text style={styles.icpCategory}>{item.category}</Text>
                    <StatusBadge type="epistemic" status={item.status} size="sm" />
                  </View>

                  <Text style={styles.icpValue}>{item.value}</Text>

                  {item.confidence && item.confidence !== 'none' ? (
                    <Text style={styles.confidenceText}>
                      Confidence: <Text style={styles.confidenceValue}>{item.confidence}</Text>
                    </Text>
                  ) : null}

                  {item.evidence ? (
                    <View style={styles.evidenceBox}>
                      <Text style={styles.evidenceLabel}>Evidence from copy:</Text>
                      <Text style={styles.evidenceText}>"{item.evidence}"</Text>
                    </View>
                  ) : null}
                </View>
              ))}
            </View>
          </View>
        </View>

        {/* 6. Competitor Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>📍 Local Competitor Comparison</Text>
            <Text style={styles.sectionSubtitle}>
              Benchmarking against nearby clinics in the same category.
            </Text>
          </View>

          <View style={styles.competitorCard}>
            {/* Disclaimer pill */}
            <View style={styles.disclaimerBadge}>
              <Text style={styles.disclaimerText}>ℹ {data.competitors.disclaimer}</Text>
            </View>

            {/* Competitor Items */}
            <View style={styles.competitorList}>
              {data.competitors.items.map((comp, i) => (
                <View key={i} style={styles.competitorRow}>
                  <View style={styles.compTop}>
                    <Text style={styles.compName}>{comp.name}</Text>
                    <View style={styles.ratingBadge}>
                      <Text style={styles.ratingStar}>★</Text>
                      <Text style={styles.ratingNumber}>
                        {comp.rating} ({comp.reviewCount})
                      </Text>
                    </View>
                  </View>
                  <Text style={styles.compHighlight}>{comp.highlight}</Text>
                </View>
              ))}
            </View>

            <View style={styles.contentDivider} />

            {/* Strengths & Opportunities */}
            <View style={styles.insightBox}>
              <Text style={styles.insightTitle}>YOUR STRENGTHS</Text>
              {data.competitors.strengths.map((str, i) => (
                <Text key={i} style={styles.insightItem}>
                  ✓ {str}
                </Text>
              ))}

              <Text style={[styles.insightTitle, { marginTop: 12 }]}>OPPORTUNITIES</Text>
              {data.competitors.opportunities.map((opp, i) => (
                <Text key={i} style={styles.insightItem}>
                  ▲ {opp}
                </Text>
              ))}
            </View>
          </View>
        </View>

        {/* 7. Bigger Projects Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>🚀 Longer-Term Improvements</Text>
            <Text style={styles.sectionSubtitle}>
              Strategic projects that compound visibility over time.
            </Text>
          </View>

          {data.biggerProjects.map((proj) => (
            <View key={proj.id} style={styles.projectCard}>
              <View style={styles.projectHeader}>
                <Text style={styles.projectTitle}>{proj.title}</Text>
                <View style={styles.projectImpactBadge}>
                  <Text style={styles.projectImpactText}>{proj.impact} Impact</Text>
                </View>
              </View>

              <Text style={styles.projectWhy}>{proj.why}</Text>

              <View style={styles.projectFooter}>
                <Text style={styles.effortLabel}>
                  Estimated Effort: <Text style={styles.effortValue}>{proj.estimatedEffort}</Text>
                </Text>
              </View>
            </View>
          ))}
        </View>

        {/* Bottom Action */}
        <TouchableOpacity style={styles.bottomResetBtn} onPress={onReset} activeOpacity={0.85}>
          <Text style={styles.bottomResetText}>Analyse Another Website</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: THEME.colors.background,
  },
  container: {
    padding: THEME.spacing.md,
    paddingTop: THEME.spacing.sm,
    paddingBottom: THEME.spacing.xxl,
  },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: THEME.spacing.md,
  },
  siteHeader: {
    flex: 1,
  },
  tagline: {
    fontSize: 10,
    fontWeight: '800',
    color: THEME.colors.primaryLight,
    letterSpacing: 1,
    marginBottom: 2,
  },
  businessTitle: {
    fontSize: 20,
    fontWeight: '800',
    color: THEME.colors.textPrimary,
  },
  domainText: {
    fontSize: 12,
    color: THEME.colors.textSecondary,
    marginTop: 2,
  },
  newAuditBtn: {
    backgroundColor: THEME.colors.surfaceLight,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: THEME.borderRadius.sm,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  newAuditText: {
    fontSize: 12,
    fontWeight: '700',
    color: THEME.colors.primaryLight,
  },
  summaryCard: {
    backgroundColor: THEME.colors.surface,
    borderRadius: THEME.borderRadius.lg,
    padding: THEME.spacing.lg,
    borderWidth: 1,
    borderColor: THEME.colors.border,
    marginBottom: THEME.spacing.lg,
  },
  summaryHeadline: {
    fontSize: 18,
    fontWeight: '800',
    color: THEME.colors.textPrimary,
    marginBottom: 6,
  },
  summaryNarrative: {
    fontSize: 14,
    color: THEME.colors.textSecondary,
    lineHeight: 20,
    marginBottom: THEME.spacing.md,
  },
  metricsRow: {
    flexDirection: 'row',
    gap: 8,
  },
  metricBox: {
    flex: 1,
    paddingVertical: 12,
    paddingHorizontal: 8,
    borderRadius: THEME.borderRadius.md,
    alignItems: 'center',
    borderWidth: 1,
  },
  metricPass: {
    backgroundColor: THEME.colors.passBg,
    borderColor: THEME.colors.passBorder,
  },
  metricWarn: {
    backgroundColor: THEME.colors.warnBg,
    borderColor: THEME.colors.warnBorder,
  },
  metricFail: {
    backgroundColor: THEME.colors.failBg,
    borderColor: THEME.colors.failBorder,
  },
  metricNumber: {
    fontSize: 22,
    fontWeight: '900',
    color: THEME.colors.textPrimary,
  },
  metricLabel: {
    fontSize: 11,
    fontWeight: '600',
    color: THEME.colors.textSecondary,
    marginTop: 2,
    textAlign: 'center',
  },
  section: {
    marginBottom: THEME.spacing.lg,
  },
  sectionHeader: {
    marginBottom: THEME.spacing.sm,
  },
  sectionTitle: {
    fontSize: 17,
    fontWeight: '800',
    color: THEME.colors.textPrimary,
  },
  sectionSubtitle: {
    fontSize: 12,
    color: THEME.colors.textMuted,
    marginTop: 2,
    lineHeight: 16,
  },
  contentCard: {
    backgroundColor: THEME.colors.surface,
    borderRadius: THEME.borderRadius.md,
    padding: THEME.spacing.md,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  cardSectionLabel: {
    fontSize: 10,
    fontWeight: '800',
    color: THEME.colors.textMuted,
    letterSpacing: 0.8,
    marginBottom: 8,
  },
  chipsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  serviceChip: {
    backgroundColor: THEME.colors.surfaceLight,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: THEME.borderRadius.sm,
    borderWidth: 1,
    borderColor: THEME.colors.borderLight,
  },
  serviceChipText: {
    fontSize: 12,
    color: THEME.colors.textPrimary,
    fontWeight: '600',
  },
  contentDivider: {
    height: 1,
    backgroundColor: THEME.colors.border,
    marginVertical: 12,
  },
  contentStatRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  statLabel: {
    fontSize: 13,
    color: THEME.colors.textSecondary,
  },
  statValue: {
    fontSize: 13,
    fontWeight: '700',
    color: THEME.colors.textPrimary,
  },
  icpCard: {
    backgroundColor: THEME.colors.surface,
    borderRadius: THEME.borderRadius.md,
    padding: THEME.spacing.md,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  icpSummary: {
    fontSize: 13,
    color: THEME.colors.textSecondary,
    lineHeight: 18,
    marginBottom: 12,
  },
  icpList: {
    gap: 10,
  },
  icpItem: {
    backgroundColor: 'rgba(15, 23, 42, 0.5)',
    borderRadius: THEME.borderRadius.sm,
    padding: 10,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  icpItemHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  icpCategory: {
    fontSize: 13,
    fontWeight: '700',
    color: THEME.colors.textPrimary,
  },
  icpValue: {
    fontSize: 14,
    color: THEME.colors.primaryLight,
    fontWeight: '600',
    marginBottom: 4,
  },
  confidenceText: {
    fontSize: 11,
    color: THEME.colors.textMuted,
    marginBottom: 6,
  },
  confidenceValue: {
    color: THEME.colors.textSecondary,
    fontWeight: '700',
    textTransform: 'capitalize',
  },
  evidenceBox: {
    backgroundColor: THEME.colors.background,
    padding: 8,
    borderRadius: 6,
    borderLeftWidth: 2,
    borderLeftColor: THEME.colors.primary,
  },
  evidenceLabel: {
    fontSize: 10,
    fontWeight: '700',
    color: THEME.colors.textMuted,
    marginBottom: 2,
  },
  evidenceText: {
    fontSize: 11,
    color: THEME.colors.textSecondary,
    fontStyle: 'italic',
  },
  competitorCard: {
    backgroundColor: THEME.colors.surface,
    borderRadius: THEME.borderRadius.md,
    padding: THEME.spacing.md,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  disclaimerBadge: {
    backgroundColor: 'rgba(56, 189, 248, 0.1)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    marginBottom: 12,
    alignSelf: 'flex-start',
  },
  disclaimerText: {
    fontSize: 11,
    color: THEME.colors.primaryLight,
    fontWeight: '600',
  },
  competitorList: {
    gap: 8,
  },
  competitorRow: {
    backgroundColor: 'rgba(15, 23, 42, 0.4)',
    borderRadius: THEME.borderRadius.sm,
    padding: 10,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  compTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  compName: {
    fontSize: 14,
    fontWeight: '700',
    color: THEME.colors.textPrimary,
  },
  ratingBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
  },
  ratingStar: {
    color: '#F59E0B',
    fontSize: 12,
  },
  ratingNumber: {
    fontSize: 12,
    fontWeight: '700',
    color: THEME.colors.textPrimary,
  },
  compHighlight: {
    fontSize: 12,
    color: THEME.colors.textSecondary,
    lineHeight: 16,
  },
  insightBox: {
    backgroundColor: 'rgba(15, 23, 42, 0.4)',
    borderRadius: THEME.borderRadius.sm,
    padding: 10,
  },
  insightTitle: {
    fontSize: 11,
    fontWeight: '800',
    color: THEME.colors.primaryLight,
    letterSpacing: 0.8,
    marginBottom: 4,
  },
  insightItem: {
    fontSize: 12,
    color: THEME.colors.textSecondary,
    lineHeight: 18,
  },
  projectCard: {
    backgroundColor: THEME.colors.surface,
    borderRadius: THEME.borderRadius.md,
    padding: THEME.spacing.md,
    borderWidth: 1,
    borderColor: THEME.colors.border,
    marginBottom: 10,
  },
  projectHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 6,
  },
  projectTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: THEME.colors.textPrimary,
    flex: 1,
    marginRight: 8,
  },
  projectImpactBadge: {
    backgroundColor: THEME.colors.passBg,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: THEME.colors.passBorder,
  },
  projectImpactText: {
    fontSize: 10,
    fontWeight: '700',
    color: THEME.colors.pass,
  },
  projectWhy: {
    fontSize: 13,
    color: THEME.colors.textSecondary,
    lineHeight: 18,
    marginBottom: 10,
  },
  projectFooter: {
    borderTopWidth: 1,
    borderTopColor: THEME.colors.border,
    paddingTop: 8,
  },
  effortLabel: {
    fontSize: 12,
    color: THEME.colors.textMuted,
  },
  effortValue: {
    color: THEME.colors.textPrimary,
    fontWeight: '700',
  },
  bottomResetBtn: {
    backgroundColor: THEME.colors.primary,
    borderRadius: THEME.borderRadius.md,
    paddingVertical: 16,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: THEME.spacing.md,
    marginBottom: THEME.spacing.lg,
  },
  bottomResetText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
});
