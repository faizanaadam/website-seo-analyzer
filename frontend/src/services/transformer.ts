import {
  AnalysisApiResponse,
  AnalysisReportData,
  TechnicalCheckItem,
  QuickWinItem,
  ICPFindingItem,
  CompetitorItem,
  ProjectItem,
} from '../types/analysis';

/**
 * Derives a readable, professional business name from page title or URL.
 */
export function deriveBusinessName(title?: string | null, url: string = ''): string {
  if (title && title.trim()) {
    const clean = title.trim();
    // Exclude generic/error titles
    const isGeneric = /^(access denied|home|homepage|index|welcome|403 forbidden|404 not found|error)/i.test(clean);
    if (!isGeneric) {
      // Split on common branding separators: |, -, –, —, :, •
      const segments = clean.split(/\s+[|\-–—:•]\s+/);
      const candidate = segments[0].trim();
      if (candidate.length >= 2 && candidate.length <= 50) {
        return candidate;
      }
    }
  }

  // Fallback to domain name
  try {
    const domainMatch = url.match(/^(?:https?:\/\/)?(?:www\.)?([^\/:]+)/i);
    if (domainMatch && domainMatch[1]) {
      const hostname = domainMatch[1];
      const mainPart = hostname.split('.')[0];
      // Format kebab/snake case or compound words e.g. "tajhotels" -> "Taj Hotels", "brightsmile" -> "Bright Smile"
      const formatted = mainPart
        .replace(/[-_]+/g, ' ')
        .replace(/([a-z])([A-Z])/g, '$1 $2')
        .replace(/([a-zA-Z]{2,})(hotels?|clinic|dentistry|dentist|repair|auto|care|shop|store|group|agency|tech|solutions|services)\b/gi, '$1 $2')
        .replace(/\s+/g, ' ')
        .trim();

      return formatted.replace(/\b\w/g, (c) => c.toUpperCase()) || hostname;
    }
  } catch (e) {
    // Ignore error
  }

  return 'Target Website';
}

/**
 * Dynamically generates Quick Wins from actual technical SEO and PageSpeed findings.
 */
export function generateQuickWins(response: AnalysisApiResponse): QuickWinItem[] {
  const quickWins: QuickWinItem[] = [];
  const findings = response.technical_seo?.findings || [];

  for (const f of findings) {
    if (f.status === 'fail' || f.status === 'needs_attention') {
      const id = f.id;
      if (id === 'image_alt_tags') {
        quickWins.push({
          id: 'qw-alt',
          title: 'Add alt text to images missing descriptions',
          impact: 'Medium',
          timeEstimate: '15 minutes',
          why: f.why_it_matters || 'Screen readers and search bots use image alt tags to understand visual content.',
        });
      } else if (id === 'meta_description') {
        quickWins.push({
          id: 'qw-meta',
          title: 'Add or optimize homepage meta description',
          impact: 'High',
          timeEstimate: '10 minutes',
          why: f.why_it_matters || 'A compelling meta description improves click-through rates from Google search results.',
        });
      } else if (id === 'structured_data') {
        quickWins.push({
          id: 'qw-schema',
          title: 'Implement Schema.org structured data',
          impact: 'High',
          timeEstimate: '30 minutes',
          why: f.why_it_matters || 'Schema helps search engines display rich snippets, reviews, and address information.',
        });
      } else if (id === 'headings_structure' || id === 'heading_structure') {
        quickWins.push({
          id: 'qw-h1',
          title: 'Organize heading hierarchy with a primary H1',
          impact: 'Medium',
          timeEstimate: '15 minutes',
          why: f.why_it_matters || 'A clear H1 heading establishes the core subject of the page for search engines.',
        });
      } else if (id === 'robots_txt_sitemap' || id === 'sitemap') {
        quickWins.push({
          id: 'qw-sitemap',
          title: 'Submit XML sitemap and configure robots.txt',
          impact: 'Medium',
          timeEstimate: '20 minutes',
          why: f.why_it_matters || 'XML sitemaps help Google discover and index all your important subpages.',
        });
      } else if (id === 'ssl_https' || id === 'https') {
        quickWins.push({
          id: 'qw-ssl',
          title: 'Enforce HTTPS security across all pages',
          impact: 'High',
          timeEstimate: '20 minutes',
          why: f.why_it_matters || 'HTTPS is a confirmed ranking factor and protects user browsing privacy.',
        });
      } else if (id === 'broken_internal_links') {
        quickWins.push({
          id: 'qw-broken',
          title: 'Fix broken internal links (404 errors)',
          impact: 'High',
          timeEstimate: '20 minutes',
          why: f.why_it_matters || 'Broken links degrade user experience and waste search engine crawl budget.',
        });
      } else if (id === 'bot_protection_detected') {
        quickWins.push({
          id: 'qw-waf',
          title: 'Review bot protection / WAF settings for search crawlers',
          impact: 'High',
          timeEstimate: '25 minutes',
          why: 'Ensure verified search engine crawlers (Googlebot, Bingbot) are whitelisted through your firewall.',
        });
      } else {
        quickWins.push({
          id: `qw-${f.id}`,
          title: f.title || 'Improve technical SEO factor',
          impact: f.status === 'fail' ? 'High' : 'Medium',
          timeEstimate: '20 minutes',
          why: f.why_it_matters || f.suggested_action,
        });
      }
    }
  }

  // Check PageSpeed for quick win
  const psi = response.pagespeed;
  if (psi?.status === 'available' && typeof psi.performance_score === 'number' && psi.performance_score < 70) {
    quickWins.push({
      id: 'qw-pagespeed',
      title: 'Optimize mobile image sizes and JavaScript execution',
      impact: 'High',
      timeEstimate: '45 minutes',
      why: `Mobile performance score is ${psi.performance_score}/100. Faster loading directly boosts search rankings and conversions.`,
    });
  }

  // Fallback if the site is in top condition and has zero issues
  if (quickWins.length === 0) {
    quickWins.push(
      {
        id: 'qw-healthy-1',
        title: 'Maintain high technical SEO standards',
        impact: 'Low',
        timeEstimate: 'Ongoing',
        why: 'All core technical SEO checks passed. Continue publishing high-depth content.',
      },
      {
        id: 'qw-healthy-2',
        title: 'Monitor Google Search Console for crawl anomalies',
        impact: 'Low',
        timeEstimate: '15 minutes / month',
        why: 'Regular monitoring ensures new subpages are indexed promptly.',
      }
    );
  }

  return quickWins.slice(0, 3);
}

/**
 * Transforms raw backend API response into frontend AnalysisReportData.
 */
export function transformApiResponseToReport(
  apiResponse: AnalysisApiResponse,
  userEnteredUrl: string
): AnalysisReportData {
  const targetUrl = apiResponse.target_url || userEnteredUrl;
  const rawTitle = apiResponse.fetch_data?.parsed_data?.title;
  const businessName = deriveBusinessName(rawTitle, targetUrl);

  // Technical SEO summary & findings
  const techSummary = apiResponse.technical_seo?.summary || {
    passed_count: 0,
    needs_attention_count: 0,
    issues_count: 0,
    total_checks: 0,
    health_score: 0,
    summary_text: apiResponse.message || 'Analysis complete.',
  };

  const technicalChecks: TechnicalCheckItem[] = (apiResponse.technical_seo?.findings || []).map((f) => ({
    id: f.id,
    name: f.title,
    status: f.status,
    summary: f.summary,
    whyItMatters: f.why_it_matters,
    evidence: f.evidence_found,
    suggestedAction: f.suggested_action,
  }));

  // Check if crawler was blocked by edge firewall / WAF challenge
  const isAccessBlocked = Boolean(
    apiResponse.fetch_data?.content_accessible === false ||
    apiResponse.content_analysis?.is_inconclusive ||
    apiResponse.technical_seo?.summary?.is_content_blocked ||
    apiResponse.fetch_data?.error_type === 'bot_protection_detected' ||
    (apiResponse.fetch_data?.status_code && [403, 429].includes(apiResponse.fetch_data.status_code))
  );

  const reliabilityNotice =
    apiResponse.technical_seo?.summary?.reliability_notice ||
    apiResponse.content_analysis?.inconclusive_reason ||
    (isAccessBlocked
      ? 'Automated crawler access was challenged by edge security (HTTP 403/WAF). Content-level analysis is inconclusive.'
      : null);

  // Quick wins
  const quickWins = generateQuickWins(apiResponse);

  // Content analysis
  const contentData = apiResponse.content_analysis;
  const isContentInconclusive = Boolean(contentData?.is_inconclusive || isAccessBlocked);
  const servicesDetected = isContentInconclusive ? [] : (contentData?.services_structure?.detected_services || []);
  const dedicatedServicePages = isContentInconclusive ? false : (contentData?.services_structure?.has_dedicated_service_pages || false);
  const homepageWordCount = isContentInconclusive ? 0 : (contentData?.homepage_word_count || apiResponse.fetch_data?.parsed_data?.visible_word_count || 0);

  // CTAs
  const ctaList: string[] = [];
  if (!isContentInconclusive && contentData?.ctas) {
    if (contentData.ctas.phones && contentData.ctas.phones.length > 0) {
      ctaList.push(`Phone Call (${contentData.ctas.phones[0]})`);
    }
    if (contentData.ctas.emails && contentData.ctas.emails.length > 0) {
      ctaList.push(`Email (${contentData.ctas.emails[0]})`);
    }
    if (contentData.ctas.whatsapp && contentData.ctas.whatsapp.length > 0) {
      ctaList.push('WhatsApp Chat');
    }
    if (contentData.ctas.booking_providers && contentData.ctas.booking_providers.length > 0) {
      ctaList.push(`${contentData.ctas.booking_providers.join(', ')} Booking`);
    } else if (contentData.ctas.booking_links && contentData.ctas.booking_links.length > 0) {
      ctaList.push('Online Appointment Link');
    }
  }

  if (ctaList.length === 0) {
    ctaList.push(isContentInconclusive ? 'Inconclusive (WAF challenge)' : 'None detected');
  }

  const contentNotes = isContentInconclusive
    ? (contentData?.summary || 'Content analysis is inconclusive because the website returned an edge security firewall challenge (HTTP 403 / WAF).')
    : (contentData?.summary || 'Visible homepage content evaluated.');

  // Inferred category & Context Intelligence
  const contextIntel = apiResponse.context_intelligence;
  const bizContext = contextIntel?.business_context;
  const audContext = contextIntel?.audience_context;

  const category = bizContext?.category || apiResponse.technical_seo?.inferred_category || 'unknown';
  const categoryLabel = category === 'unknown' ? 'General' : category.charAt(0).toUpperCase() + category.slice(1);
  const addressVal = isContentInconclusive ? null : contentData?.contact_info?.address;
  const hasLocalPresence = Boolean(addressVal || ['local_business', 'healthcare', 'restaurant'].includes(category));

  // Target audience resolution
  let targetAudienceVal = 'Inconclusive';
  let targetAudienceStatus: 'fact' | 'inference' | 'unknown' | 'inconclusive' = 'inconclusive';
  let targetAudienceConf: 'high' | 'medium' | 'low' = 'low';
  let targetAudienceEvidence = 'Insufficient observable website content to reliably determine the intended audience.';

  if (audContext) {
    targetAudienceVal = audContext.target_audience;
    targetAudienceConf = audContext.confidence;
    targetAudienceStatus = audContext.reliability === 'inconclusive' ? 'inconclusive' : 'inference';
    targetAudienceEvidence = audContext.evidence.join('; ') || targetAudienceEvidence;
  } else if (!isContentInconclusive && category !== 'unknown') {
    targetAudienceVal = `Prospective customers looking for ${categoryLabel} offerings`;
    targetAudienceStatus = 'inference';
    targetAudienceConf = 'medium';
    targetAudienceEvidence = `Inferred from observable ${category} terminology and visible keywords.`;
  }

  const icpItems: ICPFindingItem[] = [
    {
      category: 'Target Audience',
      value: targetAudienceVal,
      status: targetAudienceStatus,
      confidence: targetAudienceConf,
      evidence: targetAudienceEvidence,
    },
    {
      category: 'Geographic Reach',
      value: addressVal
        ? addressVal
        : (isContentInconclusive
          ? 'Inconclusive (Crawler challenged)'
          : (['technology', 'saas', 'ecommerce'].includes(category)
            ? 'Global / National digital reach'
            : 'Online / Regional focus')),
      status: addressVal ? 'fact' : (isContentInconclusive ? 'inconclusive' : (['technology', 'saas'].includes(category) ? 'inference' : 'unknown')),
      confidence: addressVal ? 'high' : (isContentInconclusive ? 'low' : 'medium'),
      evidence: addressVal
        ? `Directly observed from Schema.org address: "${addressVal}"`
        : (isContentInconclusive
          ? 'Physical address could not be verified due to WAF challenge.'
          : (['technology', 'saas'].includes(category)
            ? 'Software and digital platform services operate nationally or globally without a single physical storefront constraint.'
            : 'No specific physical street address detected in structured data.')),
    },
    {
      category: 'Service Architecture',
      value: isContentInconclusive
        ? 'Inconclusive (Automated crawler blocked)'
        : (dedicatedServicePages
          ? `Multi-page service architecture (${contentData?.services_structure?.service_pages_count || servicesDetected.length} dedicated pages)`
          : (servicesDetected.length > 0
            ? `Homepage-centric capability presentation (${servicesDetected.length} offerings detected)`
            : 'Services could not be reliably identified from analyzed content')),
      status: isContentInconclusive ? 'inconclusive' : 'fact',
      confidence: isContentInconclusive ? 'low' : (servicesDetected.length > 0 ? 'high' : 'low'),
      evidence: isContentInconclusive
        ? 'Internal subpages could not be crawled because crawler was challenged by edge firewall.'
        : (servicesDetected.length > 0
          ? `Deterministic crawl identified ${servicesDetected.length} service/solution offerings.`
          : 'No dedicated service sections or procedure subpages identified.'),
    },
  ];

  // Strengths & Opportunities (Fallback derived from technical checks)
  const strengths: string[] = [];
  const opportunities: string[] = [];

  for (const c of technicalChecks) {
    if (c.status === 'pass' && strengths.length < 3) {
      strengths.push(`${c.name}: ${c.summary}`);
    } else if ((c.status === 'fail' || c.status === 'needs_attention') && !c.summary?.startsWith('Inconclusive') && opportunities.length < 3) {
      opportunities.push(`${c.name}: ${c.suggestedAction || c.summary}`);
    }
  }

  if (strengths.length === 0) {
    strengths.push('Active website accessible via standard web protocols');
  }
  if (opportunities.length === 0) {
    if (isAccessBlocked) {
      opportunities.push('Bot Protection: Review CDN/WAF logs to confirm verified search engine crawlers can access public pages');
    } else {
      opportunities.push('Maintain high uptime and monitor ongoing Google indexing status');
    }
  }

  // Real Competitors from Google Places (Phase 7)
  const rawCompetitors = apiResponse.competitors;
  const compStatus = rawCompetitors?.status || 'unavailable';
  const compItems: CompetitorItem[] = (rawCompetitors?.competitors || []).map((c) => ({
    place_id: c.place_id,
    name: c.name,
    rating: c.rating,
    reviewCount: c.review_count,
    address: c.address,
    distance_km: c.distance_km,
    website_url: c.website_url,
    category: c.category,
    source: c.source || 'google_places',
    highlight: c.highlight || 'Verified local competitor via Google Places.',
  }));

  const compStrengths: string[] = (rawCompetitors?.strengths && rawCompetitors.strengths.length > 0)
    ? rawCompetitors.strengths
    : strengths;

  const compOpportunities: string[] = (rawCompetitors?.opportunities && rawCompetitors.opportunities.length > 0)
    ? rawCompetitors.opportunities
    : opportunities;

  // Bigger Projects (Context-Aware)
  const biggerProjects: ProjectItem[] = [];
  if (isAccessBlocked) {
    biggerProjects.push({
      id: 'bp-waf',
      title: 'Review CDN & WAF crawler whitelist configuration',
      impact: 'High',
      estimatedEffort: '1–2 days',
      why: 'Review CDN/WAF logs and verified bot rules to confirm that legitimate search engine crawlers (Googlebot, Bingbot) can access public content.',
    });
  }

  // Local SEO projects ONLY if verified local presence exists
  if (hasLocalPresence) {
    biggerProjects.push({
      id: 'bp-gmb',
      title: 'Optimize Google Business Profile & Local Citations',
      impact: 'High',
      estimatedEffort: '1–2 weeks',
      why: 'Local map pack rankings and nearby customer conversions depend on complete Google Business Profile signals and citation accuracy.',
    });

    let reviewWhy = 'Customer reviews on Google Maps and Local Pack are top factors for customer trust and organic discovery.';
    if (rawCompetitors?.status === 'available' && rawCompetitors.competitors.length > 0) {
      const revs = rawCompetitors.competitors.map((c) => c.review_count || 0).filter((r) => r > 0);
      if (revs.length > 0) {
        const avg = Math.round(revs.reduce((a, b) => a + b, 0) / revs.length);
        reviewWhy = `Top local competitors average ~${avg} Google reviews. A systematic review collection workflow helps build organic prominence and customer trust.`;
      }
    }

    biggerProjects.push({
      id: 'bp-reviews',
      title: 'Establish a systematic Google Review collection workflow',
      impact: 'High',
      estimatedEffort: '1–2 weeks',
      why: reviewWhy,
    });
  } else if (['technology', 'saas'].includes(category)) {
    biggerProjects.push({
      id: 'bp-tech-solutions',
      title: 'Build dedicated solution and use-case landing pages',
      impact: 'High',
      estimatedEffort: '2–4 weeks',
      why: 'Enterprise buyers and engineering teams search by specific use cases, integrations, and pain points rather than broad category terms.',
    });
    biggerProjects.push({
      id: 'bp-tech-docs',
      title: 'Publish technical documentation, case studies, and thought leadership',
      impact: 'High',
      estimatedEffort: '2–3 weeks',
      why: 'In-depth architecture overviews, developer guides, and verifiable case studies drive high-intent organic B2B search traffic.',
    });
  } else if (category === 'hospitality') {
    biggerProjects.push({
      id: 'bp-hosp-booking',
      title: 'Optimize direct room booking funnel and accommodation schema',
      impact: 'High',
      estimatedEffort: '2–3 weeks',
      why: 'Direct reservations generate higher margin and capture search queries for luxury rooms, suites, and venue amenities.',
    });
    biggerProjects.push({
      id: 'bp-hosp-guides',
      title: 'Create localized destination and area attraction guides',
      impact: 'Medium',
      estimatedEffort: '2–4 weeks',
      why: 'Travelers frequently search for area guides, dining, and local experiences when selecting luxury hotels and resorts.',
    });
  } else {
    // General / Unknown category
    if (!isContentInconclusive && !dedicatedServicePages) {
      biggerProjects.push({
        id: 'bp-pages',
        title: 'Build dedicated landing pages for individual offerings',
        impact: 'High',
        estimatedEffort: '2–4 weeks',
        why: 'Dedicated subpages allow search engines to rank your business for specific high-intent search queries.',
      });
    }
    biggerProjects.push({
      id: 'bp-content-depth',
      title: 'Expand content depth and topic authority across core pages',
      impact: 'Medium',
      estimatedEffort: '2–3 weeks',
      why: 'Comprehensive content addressing user search intent improves organic search rankings and topical authority.',
    });
  }

  return {
    targetUrl,
    businessName,
    completedAt: 'Just now',
    isAccessBlocked,
    reliabilityNotice,
    overall: {
      passedCount: techSummary.passed_count,
      needsAttentionCount: techSummary.needs_attention_count,
      issuesCount: techSummary.issues_count,
      summaryText: techSummary.summary_text,
      healthScore: techSummary.health_score,
    },
    quickWins,
    technicalChecks,
    content: {
      servicesDetected,
      dedicatedServicePages,
      homepageWordCount,
      callToActionDetected: ctaList,
      notes: contentNotes,
      contactInfo: contentData?.contact_info,
      is_inconclusive: isContentInconclusive,
      inconclusive_reason: contentData?.inconclusive_reason,
    },
    pagespeed: apiResponse.pagespeed,
    ai_insights: apiResponse.ai_insights,
    icp: {
      summary: `Automated audience analysis for ${businessName}.`,
      items: icpItems,
    },
    competitors: {
      status: compStatus,
      searchCategory: rawCompetitors?.search_category,
      searchLocation: rawCompetitors?.search_location,
      items: compItems,
      strengths: compStrengths,
      opportunities: compOpportunities,
      reason: rawCompetitors?.reason,
      limitations: rawCompetitors?.limitations,
    },
    biggerProjects,
  };
}
