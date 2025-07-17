SUMMARIZATION_PROMPT = """ROLE: Expert conversation analyst and summarizer

TASK: Analyze the following transcribed conversation and create a concise, informative summary.

CONTEXT: This transcription comes from an audio recording and may contain:
- Multiple speakers
- Background noise artifacts
- Incomplete sentences
- Technical jargon or domain-specific terms

REQUIREMENTS:
1. Create a single, coherent paragraph (100-200 words)
2. Identify key participants and their roles
3. Capture the main topic and any critical issues
4. Note the overall tone and urgency level
5. Highlight any actionable items or decisions made

TRANSCRIPTION:
{transcription_text}

SUMMARY:"""

JUDGMENT_PROMPT = """ROLE: Senior incident analyst and decision support system

TASK: Analyze the conversation summary and determine appropriate next actions.

CONTEXT: You are evaluating a workplace conversation for potential escalation or action requirements.

CLASSIFICATION CATEGORIES:
- REPORT_TO_MANAGEMENT: Requires supervisor/manager attention
- REPORT_TO_AUTHORITIES: Legal or regulatory compliance issue
- CREATE_TICKET: Technical or operational issue needing tracking
- STORE_IN_DATABASE: Information for future reference
- URGENT_ACTION: Immediate intervention required
- NO_ACTION: Routine conversation, no follow-up needed

ANALYSIS REQUIREMENTS:
1. Assess severity level (LOW, MEDIUM, HIGH, CRITICAL)
2. Identify specific action triggers
3. Provide confidence score (0-100)
4. Include brief reasoning
5. Suggest timeline for action

OUTPUT FORMAT: Respond with a valid JSON object containing:
{{
  "severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "confidence_score": 0-100,
  "primary_action": "action_category",
  "secondary_actions": ["action1", "action2"],
  "reasoning": "brief explanation",
  "suggested_timeline": "IMMEDIATE|URGENT|SCHEDULED|ROUTINE",
  "stakeholders": ["stakeholder1", "stakeholder2"],
  "business_impact": "LOW|MEDIUM|HIGH|CRITICAL",
  "keywords": ["keyword1", "keyword2"]
}}

CONVERSATION SUMMARY:
{summary_text}

JSON ANALYSIS:"""

def get_summarization_prompt(transcription_text: str) -> str:
    """Generate the complete summarization prompt with transcription text."""
    return SUMMARIZATION_PROMPT.format(transcription_text=transcription_text)

def get_judgment_prompt(summary_text: str) -> str:
    """Generate the complete judgment prompt with summary text."""
    return JUDGMENT_PROMPT.format(summary_text=summary_text) 