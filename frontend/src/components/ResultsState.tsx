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
import { AnalysisReportData, AIRecommendationItemData } from '../types/analysis';
import { QuickWinCard } from './QuickWinCard';
import { ExpandableCard } from './ExpandableCard';
import { StatusBadge } from './StatusBadge';

interface ResultsStateProps {
  data: AnalysisReportData;
  onReset: () => void;
}

export const ResultsState: React.FC<ResultsStateProps> = ({ data, onReset }) => {
  const pagespeed = data.pagespeed;
  const hasPageSpeedMetrics = pagespeed?.status === 'available' && pagespeed.metrics;
  const score = pagespeed?.performance_score;
  const ai = data.ai_insights;

  const getScoreColorStyle = (val: number | null | undefined) => {
    if (val === null || val === undefined) return styles.metricScoreNeutral;
    if (val >= 90) return styles.metricScoreGood;
    if (val >= 50) return styles.metricScoreAvg;
    return styles.metricScorePoor;
  };

  const getAssessmentBadgeStyle = (assessment?: string | null) => {
    switch (assessment?.toLowerCase()) {
      case 'excellent':
      case 'good':
        return styles.assessmentGood;
      case 'moderate':
        return styles.assessmentModerate;
      case 'needs_improvement':
      case 'critical':
        return styles.assessmentCritical;
      default:
        return styles.assessmentNeutral;
    }
  };

  const getPriorityBadgeStyle = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'critical':
        return styles.priorityCritical;
      case 'high':
        return styles.priorityHigh;
      case 'medium':
        return styles.priorityMedium;
      default:
        return styles.priorityLow;
    }
  };

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

        {/* Reliability & Crawler Accessibility Notice */}
        {data.isAccessBlocked ? (
          <View style={styles.reliabilityWarningCard}>
            <View style={styles.reliabilityHeaderRow}>
              <Text style={styles.reliabilityIcon}>🛡</Text>
              <View style={{ flex: 1 }}>
                <Text style={styles.reliabilityWarningTitle}>
                  Automated Crawler Access Limited (WAF / Bot Protection)
                </Text>
                <Text style={styles.reliabilityWarningText}>
                  {data.reliabilityNotice || 'The target website returned an edge security challenge (HTTP 403 / Akamai / Cloudflare WAF). On-page content metrics (word count, service detection, headings, image alt text) are marked inconclusive.'}
                </Text>
              </View>
            </View>
          </View>
        ) : null}

        {/* 2. AI Business & Strategic Insights Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeaderRow}>
            <View>
              <Text style={styles.sectionTitle}>🧠 AI Business & Strategic Insights</Text>
              <Text style={styles.sectionSubtitle}>
                Executive analysis and prioritized growth opportunities powered by OpenAI.
              </Text>
            </View>
            {ai?.overall_assessment && (
              <View style={[styles.assessmentBadge, getAssessmentBadgeStyle(ai.overall_assessment)]}>
                <Text style={styles.assessmentText}>
                  {ai.overall_assessment.replace('_', ' ').toUpperCase()}
                </Text>
              </View>
            )}
          </View>

          {ai?.status === 'available' ? (
            <View style={styles.aiContainer}>
              {/* Executive Summary */}
              {ai.executive_summary ? (
                <View style={styles.aiExecutiveCard}>
                  <Text style={styles.aiCardLabel}>EXECUTIVE SUMMARY</Text>
                  <Text style={styles.aiExecutiveText}>{ai.executive_summary}</Text>
                </View>
              ) : null}

              {/* Top Priorities */}
              {ai.top_priorities && ai.top_priorities.length > 0 && (
                <View style={styles.aiPrioritiesSection}>
                  <Text style={styles.aiPrioritiesTitle}>TOP STRATEGIC PRIORITIES</Text>
                  {ai.top_priorities.map((item: AIRecommendationItemData, idx: number) => (
                    <View key={idx} style={styles.aiPriorityCard}>
                      <View style={styles.aiPriorityHeader}>
                        <View style={styles.badgeRow}>
                          <View style={[styles.priorityPill, getPriorityBadgeStyle(item.priority)]}>
                            <Text style={styles.priorityPillText}>{item.priority.toUpperCase()}</Text>
                          </View>
                          <View style={styles.categoryPill}>
                            <Text style={styles.categoryPillText}>{item.category.replace('_', ' ')}</Text>
                          </View>
                          {item.anchor_finding_id ? (
                            <View style={styles.anchorPill}>
                              <Text style={styles.anchorPillText}>🔗 {item.anchor_finding_id.replace(/_/g, ' ')}</Text>
                            </View>
                          ) : null}
                        </View>
                        <Text style={styles.effortPill}>Effort: {item.estimated_effort}</Text>
                      </View>

                      <Text style={styles.aiPriorityItemTitle}>{item.title}</Text>
                      <Text style={styles.aiPriorityExplanation}>{item.explanation}</Text>

                      <View style={styles.aiImpactBox}>
                        <Text style={styles.aiImpactLabel}>📈 Business Impact:</Text>
                        <Text style={styles.aiImpactText}>{item.business_impact}</Text>
                      </View>

                      <View style={styles.aiActionBox}>
                        <Text style={styles.aiActionLabel}>👉 Recommended Action:</Text>
                        <Text style={styles.aiActionText}>{item.recommended_action}</Text>
                      </View>
                    </View>
                  ))}
                </View>
              )}

              {/* Strengths & Quick Wins 2-column or list */}
              {ai.strengths && ai.strengths.length > 0 && (
                <View style={styles.aiStrengthsCard}>
                  <Text style={styles.aiStrengthsTitle}>VERIFIED WEBSITE STRENGTHS</Text>
                  {ai.strengths.map((str: string, i: number) => (
                    <View key={i} style={styles.aiStrengthRow}>
                      <Text style={styles.aiStrengthCheck}>✓</Text>
                      <Text style={styles.aiStrengthText}>{str}</Text>
                    </View>
                  ))}
                </View>
              )}

              {/* Limitations Notice */}
              {ai.limitations && ai.limitations.length > 0 && (
                <View style={styles.aiLimitationsCard}>
                  <Text style={styles.aiLimitationsTitle}>ℹ SCOPE & LIMITATIONS</Text>
                  {ai.limitations.map((lim: string, i: number) => (
                    <Text key={i} style={styles.aiLimitationText}>• {lim}</Text>
                  ))}
                </View>
              )}
            </View>
          ) : (
            <View style={styles.aiUnavailableCard}>
              <Text style={styles.aiUnavailableTitle}>Strategic AI Analysis Unavailable</Text>
              <Text style={styles.aiUnavailableReason}>
                Strategic AI analysis is temporarily unavailable. Your deterministic SEO and content analysis results are still complete.
              </Text>
              {ai?.reason ? (
                <Text style={styles.aiUnavailableSubReason}>Notice: {ai.reason}</Text>
              ) : null}
            </View>
          )}
        </View>

        {/* 3. Quick Wins Section */}
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

        {/* 4. Technical SEO Section */}
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

        {/* 5. Google PageSpeed Insights Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>⚡ Google PageSpeed & Core Web Vitals</Text>
            <Text style={styles.sectionSubtitle}>
              Official mobile Lighthouse performance scores and user experience vitals.
            </Text>
          </View>

          <View style={styles.psiCard}>
            {hasPageSpeedMetrics ? (
              <>
                <View style={styles.psiHeaderRow}>
                  <View>
                    <Text style={styles.psiCategoryLabel}>MOBILE PERFORMANCE SCORE</Text>
                    <Text style={styles.psiSublabel}>Simulated Moto G Power / Mobile 4G</Text>
                  </View>
                  <View style={[styles.psiScoreBadge, getScoreColorStyle(score)]}>
                    <Text style={styles.psiScoreNumber}>{score ?? 'N/A'}</Text>
                    <Text style={styles.psiScoreTotal}>/100</Text>
                  </View>
                </View>

                <View style={styles.contentDivider} />

                {/* Web Vitals Grid */}
                <View style={styles.vitalsGrid}>
                  <View style={styles.vitalBox}>
                    <Text style={styles.vitalLabel}>First Contentful Paint (FCP)</Text>
                    <Text style={styles.vitalValue}>{pagespeed?.metrics?.fcp || 'N/A'}</Text>
                  </View>
                  <View style={styles.vitalBox}>
                    <Text style={styles.vitalLabel}>Largest Contentful Paint (LCP)</Text>
                    <Text style={styles.vitalValue}>{pagespeed?.metrics?.lcp || 'N/A'}</Text>
                  </View>
                  <View style={styles.vitalBox}>
                    <Text style={styles.vitalLabel}>Cumulative Layout Shift (CLS)</Text>
                    <Text style={styles.vitalValue}>{pagespeed?.metrics?.cls !== undefined && pagespeed?.metrics?.cls !== null ? pagespeed.metrics.cls : 'N/A'}</Text>
                  </View>
                  <View style={styles.vitalBox}>
                    <Text style={styles.vitalLabel}>Total Blocking Time (TBT)</Text>
                    <Text style={styles.vitalValue}>{pagespeed?.metrics?.tbt || pagespeed?.metrics?.inp || 'N/A'}</Text>
                  </View>
                </View>
              </>
            ) : (
              <View style={styles.psiUnavailableBox}>
                <Text style={styles.psiUnavailableTitle}>Performance Data Unavailable</Text>
                <Text style={styles.psiUnavailableReason}>
                  Performance data could not be retrieved at this time. The rest of the website analysis completed successfully.
                </Text>
                {pagespeed?.reason ? (
                  <Text style={styles.psiUnavailableSubReason}>Notice: {pagespeed.reason}</Text>
                ) : null}
              </View>
            )}
          </View>
        </View>

        {/* 6. Content & Website Structure */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>📄 Content & Website Structure</Text>
            <Text style={styles.sectionSubtitle}>
              Evaluating service depth, dedicated procedure pages, and conversion pathways.
            </Text>
          </View>

          <View style={styles.contentCard}>
            {data.content.is_inconclusive || data.isAccessBlocked ? (
              <View style={styles.inconclusiveContentBox}>
                <Text style={styles.inconclusiveContentTitle}>⚠ Content Analysis Inconclusive</Text>
                <Text style={styles.inconclusiveContentText}>
                  {data.content.notes || 'The crawler encountered an automated access or bot-protection challenge (HTTP 403 / WAF). Content depth, service architecture, and word count metrics could not be extracted.'}
                </Text>
                <View style={styles.inconclusiveTipBox}>
                  <Text style={styles.inconclusiveTipText}>
                    💡 Tip: Ensure verified search engine crawlers (Googlebot, Bingbot) are whitelisted in your CDN/WAF rules so search engines can access and index your full site content.
                  </Text>
                </View>
              </View>
            ) : (
              <>
                <Text style={styles.cardSectionLabel}>
                  {data.content.dedicatedServicePages ? 'SERVICES DETECTED ACROSS SUBPAGES' : 'SERVICES / CAPABILITIES IDENTIFIED'}
                </Text>
                {data.content.servicesDetected.length > 0 ? (
                  <View style={styles.chipsRow}>
                    {data.content.servicesDetected.map((service, i) => (
                      <View key={i} style={styles.serviceChip}>
                        <Text style={styles.serviceChipText}>✓ {service}</Text>
                      </View>
                    ))}
                  </View>
                ) : (
                  <Text style={styles.noServiceText}>Services could not be reliably identified from the analyzed content.</Text>
                )}

                <View style={styles.contentDivider} />

                <View style={styles.contentStatRow}>
                  <Text style={styles.statLabel}>Dedicated Service Pages:</Text>
                  <Text style={styles.statValue}>
                    {data.content.dedicatedServicePages ? '✓ Yes (Individual service routes)' : '✕ No (Single-page presentation)'}
                  </Text>
                </View>

                <View style={styles.contentStatRow}>
                  <Text style={styles.statLabel}>Homepage Word Count:</Text>
                  <Text style={styles.statValue}>{data.content.homepageWordCount} words</Text>
                </View>

                <View style={styles.contentStatRow}>
                  <Text style={styles.statLabel}>Call-to-Action Detected:</Text>
                  <Text style={styles.statValue}>{data.content.callToActionDetected.join(', ')}</Text>
                </View>

                {data.content.contactInfo?.address && (
                  <View style={styles.contentStatRow}>
                    <Text style={styles.statLabel}>Physical Address:</Text>
                    <Text style={styles.statValue} numberOfLines={2}>{data.content.contactInfo.address}</Text>
                  </View>
                )}

                {data.content.contactInfo?.opening_hours && data.content.contactInfo.opening_hours.length > 0 && (
                  <View style={styles.contentStatRow}>
                    <Text style={styles.statLabel}>Opening Hours:</Text>
                    <Text style={styles.statValue} numberOfLines={2}>{data.content.contactInfo.opening_hours.join('; ')}</Text>
                  </View>
                )}
              </>
            )}
          </View>
        </View>

        {/* 7. Ideal Customer Profile Section */}
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

        {/* 8. Competitor Section */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>📍 Local Competitor Comparison</Text>
            <Text style={styles.sectionSubtitle}>
              Benchmarking against nearby businesses in the same category.
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

        {/* 9. Bigger Projects Section */}
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
  sectionHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
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
  assessmentBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
  },
  assessmentGood: {
    backgroundColor: THEME.colors.passBg,
    borderColor: THEME.colors.passBorder,
  },
  assessmentModerate: {
    backgroundColor: THEME.colors.warnBg,
    borderColor: THEME.colors.warnBorder,
  },
  assessmentCritical: {
    backgroundColor: THEME.colors.failBg,
    borderColor: THEME.colors.failBorder,
  },
  assessmentNeutral: {
    backgroundColor: THEME.colors.surfaceLight,
    borderColor: THEME.colors.border,
  },
  assessmentText: {
    fontSize: 10,
    fontWeight: '800',
    color: THEME.colors.textPrimary,
    letterSpacing: 0.5,
  },
  aiContainer: {
    gap: 12,
  },
  aiExecutiveCard: {
    backgroundColor: 'rgba(56, 189, 248, 0.07)',
    borderRadius: THEME.borderRadius.md,
    padding: THEME.spacing.md,
    borderWidth: 1,
    borderColor: 'rgba(56, 189, 248, 0.25)',
  },
  aiCardLabel: {
    fontSize: 10,
    fontWeight: '800',
    color: THEME.colors.primaryLight,
    letterSpacing: 1,
    marginBottom: 6,
  },
  aiExecutiveText: {
    fontSize: 14,
    color: THEME.colors.textPrimary,
    lineHeight: 21,
    fontWeight: '500',
  },
  aiPrioritiesSection: {
    gap: 10,
  },
  aiPrioritiesTitle: {
    fontSize: 11,
    fontWeight: '800',
    color: THEME.colors.textMuted,
    letterSpacing: 0.8,
    marginTop: 4,
  },
  aiPriorityCard: {
    backgroundColor: THEME.colors.surface,
    borderRadius: THEME.borderRadius.md,
    padding: THEME.spacing.md,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  aiPriorityHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  badgeRow: {
    flexDirection: 'row',
    gap: 6,
    alignItems: 'center',
  },
  priorityPill: {
    paddingHorizontal: 7,
    paddingVertical: 3,
    borderRadius: 4,
    borderWidth: 1,
  },
  priorityCritical: {
    backgroundColor: THEME.colors.failBg,
    borderColor: THEME.colors.failBorder,
  },
  priorityHigh: {
    backgroundColor: 'rgba(249, 115, 22, 0.15)',
    borderColor: 'rgba(249, 115, 22, 0.4)',
  },
  priorityMedium: {
    backgroundColor: THEME.colors.warnBg,
    borderColor: THEME.colors.warnBorder,
  },
  priorityLow: {
    backgroundColor: THEME.colors.surfaceLight,
    borderColor: THEME.colors.border,
  },
  priorityPillText: {
    fontSize: 10,
    fontWeight: '800',
    color: THEME.colors.textPrimary,
  },
  categoryPill: {
    backgroundColor: THEME.colors.surfaceLight,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: THEME.colors.borderLight,
  },
  categoryPillText: {
    fontSize: 10,
    color: THEME.colors.textSecondary,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  anchorPill: {
    backgroundColor: 'rgba(56, 189, 248, 0.1)',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: 'rgba(56, 189, 248, 0.3)',
  },
  anchorPillText: {
    fontSize: 10,
    color: THEME.colors.primaryLight,
    fontWeight: '700',
    textTransform: 'capitalize',
  },
  effortPill: {
    fontSize: 11,
    color: THEME.colors.textMuted,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  aiPriorityItemTitle: {
    fontSize: 15,
    fontWeight: '800',
    color: THEME.colors.textPrimary,
    marginBottom: 4,
  },
  aiPriorityExplanation: {
    fontSize: 13,
    color: THEME.colors.textSecondary,
    lineHeight: 18,
    marginBottom: 10,
  },
  aiImpactBox: {
    backgroundColor: 'rgba(34, 197, 94, 0.08)',
    borderRadius: 6,
    padding: 8,
    borderLeftWidth: 3,
    borderLeftColor: THEME.colors.pass,
    marginBottom: 8,
  },
  aiImpactLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: THEME.colors.pass,
    marginBottom: 2,
  },
  aiImpactText: {
    fontSize: 12,
    color: THEME.colors.textPrimary,
    lineHeight: 17,
  },
  aiActionBox: {
    backgroundColor: 'rgba(56, 189, 248, 0.08)',
    borderRadius: 6,
    padding: 8,
    borderLeftWidth: 3,
    borderLeftColor: THEME.colors.primary,
  },
  aiActionLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: THEME.colors.primaryLight,
    marginBottom: 2,
  },
  aiActionText: {
    fontSize: 12,
    color: THEME.colors.textPrimary,
    lineHeight: 17,
  },
  aiStrengthsCard: {
    backgroundColor: THEME.colors.surface,
    borderRadius: THEME.borderRadius.md,
    padding: THEME.spacing.md,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  aiStrengthsTitle: {
    fontSize: 11,
    fontWeight: '800',
    color: THEME.colors.pass,
    letterSpacing: 0.8,
    marginBottom: 8,
  },
  aiStrengthRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 6,
  },
  aiStrengthCheck: {
    fontSize: 13,
    color: THEME.colors.pass,
    fontWeight: '900',
    marginRight: 8,
  },
  aiStrengthText: {
    fontSize: 13,
    color: THEME.colors.textSecondary,
    lineHeight: 18,
    flex: 1,
  },
  aiLimitationsCard: {
    backgroundColor: 'rgba(15, 23, 42, 0.4)',
    borderRadius: THEME.borderRadius.sm,
    padding: 10,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  aiLimitationsTitle: {
    fontSize: 10,
    fontWeight: '800',
    color: THEME.colors.textMuted,
    letterSpacing: 0.8,
    marginBottom: 4,
  },
  aiLimitationText: {
    fontSize: 12,
    color: THEME.colors.textMuted,
    lineHeight: 16,
  },
  aiUnavailableCard: {
    backgroundColor: THEME.colors.surface,
    borderRadius: THEME.borderRadius.md,
    padding: THEME.spacing.md,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  aiUnavailableTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: THEME.colors.textSecondary,
    marginBottom: 4,
  },
  aiUnavailableReason: {
    fontSize: 12,
    color: THEME.colors.textMuted,
    lineHeight: 16,
  },
  aiUnavailableSubReason: {
    fontSize: 11,
    color: THEME.colors.textMuted,
    marginTop: 6,
    fontStyle: 'italic',
  },
  psiCard: {
    backgroundColor: THEME.colors.surface,
    borderRadius: THEME.borderRadius.md,
    padding: THEME.spacing.md,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  psiHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  psiCategoryLabel: {
    fontSize: 11,
    fontWeight: '800',
    color: THEME.colors.primaryLight,
    letterSpacing: 0.8,
  },
  psiSublabel: {
    fontSize: 11,
    color: THEME.colors.textMuted,
    marginTop: 2,
  },
  psiScoreBadge: {
    flexDirection: 'row',
    alignItems: 'baseline',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: THEME.borderRadius.sm,
    borderWidth: 1,
  },
  metricScoreGood: {
    backgroundColor: THEME.colors.passBg,
    borderColor: THEME.colors.passBorder,
  },
  metricScoreAvg: {
    backgroundColor: THEME.colors.warnBg,
    borderColor: THEME.colors.warnBorder,
  },
  metricScorePoor: {
    backgroundColor: THEME.colors.failBg,
    borderColor: THEME.colors.failBorder,
  },
  metricScoreNeutral: {
    backgroundColor: THEME.colors.surfaceLight,
    borderColor: THEME.colors.border,
  },
  psiScoreNumber: {
    fontSize: 20,
    fontWeight: '900',
    color: THEME.colors.textPrimary,
  },
  psiScoreTotal: {
    fontSize: 11,
    fontWeight: '600',
    color: THEME.colors.textMuted,
    marginLeft: 2,
  },
  vitalsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  vitalBox: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: 'rgba(15, 23, 42, 0.4)',
    padding: 10,
    borderRadius: THEME.borderRadius.sm,
    borderWidth: 1,
    borderColor: THEME.colors.border,
  },
  vitalLabel: {
    fontSize: 10,
    fontWeight: '700',
    color: THEME.colors.textMuted,
    marginBottom: 4,
  },
  vitalValue: {
    fontSize: 15,
    fontWeight: '800',
    color: THEME.colors.textPrimary,
  },
  psiUnavailableBox: {
    paddingVertical: 8,
  },
  psiUnavailableTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: THEME.colors.textSecondary,
    marginBottom: 4,
  },
  psiUnavailableReason: {
    fontSize: 12,
    color: THEME.colors.textMuted,
    lineHeight: 16,
  },
  psiUnavailableSubReason: {
    fontSize: 11,
    color: THEME.colors.textMuted,
    marginTop: 6,
    fontStyle: 'italic',
  },
  reliabilityWarningCard: {
    backgroundColor: 'rgba(245, 158, 11, 0.12)',
    borderRadius: THEME.borderRadius.md,
    padding: THEME.spacing.md,
    borderWidth: 1,
    borderColor: 'rgba(245, 158, 11, 0.35)',
    marginBottom: THEME.spacing.lg,
  },
  reliabilityHeaderRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
  },
  reliabilityIcon: {
    fontSize: 20,
  },
  reliabilityWarningTitle: {
    fontSize: 14,
    fontWeight: '800',
    color: THEME.colors.warn,
    marginBottom: 4,
  },
  reliabilityWarningText: {
    fontSize: 12,
    color: THEME.colors.textSecondary,
    lineHeight: 18,
  },
  inconclusiveContentBox: {
    paddingVertical: THEME.spacing.xs,
  },
  inconclusiveContentTitle: {
    fontSize: 14,
    fontWeight: '800',
    color: THEME.colors.warn,
    marginBottom: 6,
  },
  inconclusiveContentText: {
    fontSize: 13,
    color: THEME.colors.textSecondary,
    lineHeight: 18,
    marginBottom: 10,
  },
  inconclusiveTipBox: {
    backgroundColor: THEME.colors.surfaceLight,
    padding: THEME.spacing.sm,
    borderRadius: THEME.borderRadius.sm,
    borderLeftWidth: 3,
    borderLeftColor: THEME.colors.primary,
  },
  inconclusiveTipText: {
    fontSize: 12,
    color: THEME.colors.textMuted,
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
  noServiceText: {
    fontSize: 12,
    color: THEME.colors.textMuted,
    fontStyle: 'italic',
    marginBottom: 4,
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
    flex: 1,
  },
  statValue: {
    fontSize: 13,
    fontWeight: '700',
    color: THEME.colors.textPrimary,
    flex: 1,
    textAlign: 'right',
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
