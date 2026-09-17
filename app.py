import io
import json
import os
import re
import time
from pathlib import Path

import pandas as pd
import streamlit as st
from pypdf import PdfReader
from google import genai

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="CSP Outcome Mapping Generator",
    page_icon="📘",
    layout="wide",
)


# ============================================================
# FIXED COURSE OUTCOMES
# ============================================================

COS = [
    (
        "CO1",
        "Describe/Explain the social, technical, and safety-related conditions, needs, and problems observed in the community.",
        "Understand (L2)",
    ),
    (
        "CO2",
        "Apply fundamental concepts of electrical and electronics engineering to understand and address real-time problems identified in the community.",
        "Apply (L3)",
    ),
    (
        "CO3",
        "Analyze the problems, needs, existing practices, and possible solutions identified during the community service activities.",
        "Analyze (L4)",
    ),
    (
        "CO4",
        "Demonstrate professional ethics, social responsibility, teamwork, communication, and safety practices while interacting with the community and conducting service activities.",
        "Apply/Evaluate (L3/L5)",
    ),
    (
        "CO5",
        "Prepare and present a technical Community Service Project report/seminar documenting the community observations, survey findings, activities carried out, outcomes, and learning experiences using appropriate technical vocabulary and presentation tools.",
        "Create (L6)",
    ),
]


# ============================================================
# FIXED PROGRAM OUTCOMES
# ============================================================

POS = [
    (
        "PO1",
        "Engineering Knowledge: Apply knowledge of mathematics, natural science, computing, engineering fundamentals and an engineering specialization to develop solutions to complex engineering problems.",
    ),
    (
        "PO2",
        "Problem Analysis: Identify, formulate, review research literature and analyze complex engineering problems, reaching substantiated conclusions with consideration for sustainable development.",
    ),
    (
        "PO3",
        "Design/Development of Solutions: Design creative solutions for complex engineering problems and design system components/processes to meet identified needs with consideration for public health and safety, whole-life cost, net zero carbon, culture, society and environment.",
    ),
    (
        "PO4",
        "Conduct Investigations of Complex Problems: Conduct investigations of complex engineering problems using research-based knowledge including design of experiments, modelling, analysis & interpretation of data to provide valid conclusions.",
    ),
    (
        "PO5",
        "Engineering Tool Usage: Create, select and apply appropriate techniques, resources and modern engineering & IT tools, including prediction and modelling recognizing their limitations to solve complex engineering problems.",
    ),
    (
        "PO6",
        "The Engineer and The World: Analyze and evaluate societal and environmental aspects while solving complex engineering problems for its impact on sustainability with reference to economy, health, safety, societal, legal framework, culture and environment.",
    ),
    (
        "PO7",
        "Ethics: Apply ethical principles and commit to professional ethics, human values, diversity and inclusion; adhere to national & international laws.",
    ),
    (
        "PO8",
        "Individual and Collaborative Team work: Function effectively as an individual, and as a member or leader in diverse/multi-disciplinary teams.",
    ),
    (
        "PO9",
        "Communication: Communicate effectively and inclusively within the engineering community and society at large, such as being able to comprehend and write effective reports and design documentation, make effective presentations considering cultural, language, and learning differences.",
    ),
    (
        "PO10",
        "Project Management and Finance: Apply knowledge and understanding of engineering management principles and economic decision-making and apply these to one's own work, as a member and leader in a team, and to manage projects and in multidisciplinary environments.",
    ),
    (
        "PO11",
        "Life-Long Learning: Recognize the need for, and have the preparation and ability for independent and life-long learning, adaptability to new and emerging technologies and critical thinking in the broader context of technological change.",
    ),
]


# ============================================================
# FIXED PROGRAM SPECIFIC OUTCOMES
# ============================================================

PSOS = [
    (
        "PSO1",
        "Apply fundamental knowledge to analyze and solve complex problems of Electrical Machines, Control Systems, Instrumentation Systems, Power Systems and Power Electronic Systems.",
    ),
    (
        "PSO2",
        "Design electrical, electronics and interdisciplinary projects to meet industrial demands and solve real-time problems.",
    ),
    (
        "PSO3",
        "Utilize recent techniques and sustainable technologies in areas such as Control Engineering, Smart Grid, Power Quality and Advanced Power System Protection for lifelong learning.",
    ),
]


# ============================================================
# FIXED KNOWLEDGE PROFILE
# ============================================================

WKS = [
    (
        "WK1",
        "A systematic, theory-based understanding of the natural sciences applicable to the discipline and awareness of relevant social sciences.",
    ),
    (
        "WK2",
        "Conceptually-based mathematics, numerical analysis, data analysis, statistics and formal aspects of computer and information science to support detailed analysis and modelling applicable to the discipline.",
    ),
    (
        "WK3",
        "A systematic, theory-based formulation of engineering fundamentals required in the engineering discipline.",
    ),
    (
        "WK4",
        "Engineering specialist knowledge that provides theoretical frameworks and bodies of knowledge for the accepted practice areas in the engineering discipline; much is at the forefront of the discipline.",
    ),
    (
        "WK5",
        "Knowledge, including efficient resource use, environmental impacts, whole-life cost, re-use of resources, net zero carbon, and similar concepts, that supports engineering design and operations in a practice area.",
    ),
    (
        "WK6",
        "Knowledge of engineering practice (technology) in the practice areas in the engineering discipline.",
    ),
    (
        "WK7",
        "Knowledge of the role of engineering in society and identified issues in engineering practice, such as the professional responsibility of an engineer to public safety and sustainable development.",
    ),
    (
        "WK8",
        "Engagement with selected knowledge in the current research literature of the discipline, awareness of the power of critical thinking and creative approaches to evaluate emerging issues.",
    ),
    (
        "WK9",
        "Ethics, inclusive behavior and conduct. Knowledge of professional ethics, responsibilities, and norms of engineering practice. Awareness of the need for diversity by reason of ethnicity, gender, age, physical ability etc. with mutual understanding and respect, and of inclusive attitudes.",
    ),
]


# ============================================================
# FIXED WK -> PO/PSO MATRIX
# ============================================================

HEADERS = [f"PO{i}" for i in range(1, 12)] + [
    "PSO1",
    "PSO2",
    "PSO3",
]

FIXED_WK_MATRIX = [
    [2, 2, "-", "-", "-", 1, "-", "-", "-", "-", "-", "-", "-", "-"],
    [2, 2, "-", "-", 2, "-", "-", "-", "-", "-", "-", 1, "-", "-"],
    [3, 3, "-", "-", "-", "-", "-", "-", "-", "-", "-", 2, "-", "-"],
    [3, 3, "-", "-", "-", "-", "-", "-", "-", "-", "-", 3, 1, "-"],
    ["-", "-", 3, "-", "-", 3, "-", "-", "-", "-", "-", "-", 2, 2],
    ["-", "-", "-", "-", 3, "-", "-", "-", "-", "-", "-", "-", 3, 3],
    ["-", "-", "-", "-", "-", 3, "-", "-", "-", "-", "-", "-", "-", "-"],
    ["-", "-", "-", 3, "-", "-", "-", "-", "-", "-", 3, "-", "-", 2],
    ["-", "-", "-", "-", "-", "-", 3, "-", "-", "-", "-", "-", "-", "-"],
]


# ============================================================
# FIXED SDG 1-17 LIST
# ============================================================

SDGS = {
    1: "End poverty in all its forms everywhere",
    2: "End hunger, achieve food security and improved nutrition and promote sustainable agriculture",
    3: "Ensure healthy lives and promote well-being for all at all ages",
    4: "Ensure inclusive and equitable quality education and promote lifelong learning opportunities for all",
    5: "Achieve gender equality and empower all women and girls",
    6: "Ensure availability and sustainable management of water and sanitation for all",
    7: "Ensure access to affordable, reliable, sustainable and modern energy for all",
    8: "Promote sustained, inclusive, and sustainable economic growth, full and productive employment and decent work for all",
    9: "Build resilient infrastructure, promote inclusive and sustainable industrialization and foster innovation",
    10: "Reduce inequality within and among countries",
    11: "Make cities and human settlements inclusive, safe, resilient and sustainable",
    12: "Ensure sustainable consumption and production patterns",
    13: "Take urgent action to combat climate change and its impacts",
    14: "Conserve and sustainably use the oceans, seas and marine resources for sustainable development",
    15: "Protect, restore and promote sustainable use of terrestrial ecosystems, sustainably manage forests, combat desertification, and halt and reverse land degradation and halt biodiversity loss",
    16: "Promote peaceful and inclusive societies for sustainable development, provide access to justice for all and build effective, accountable and inclusive institutions at all levels",
    17: "Strengthen the means of implementation and revitalize the global partnership for sustainable development",
}


# ============================================================
# PDF EXTRACTION
# ============================================================

def extract_text(uploaded_file):
    reader = PdfReader(uploaded_file)

    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""

        pages.append(
            f"\n[PAGE {page_number}]\n{page_text}"
        )

    return "\n".join(pages)


def clean_text(text):
    text = text or ""
    text = text.replace("\xa0", " ")
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_title(text):
    patterns = [
        r"(?:project title|title of the project)\s*[:\-]\s*(.{5,180})",
        r"(?:project)\s*[:\-]\s*(.{5,180})",
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            return clean_text(match.group(1))[:180]

    return "Community Service Project"


# ============================================================
# GEMINI
# ============================================================

def get_gemini_api_key():
    key_file = (
        Path(".streamlit")
        / "gemini_api_key.txt"
    )

    if key_file.exists():
        key = key_file.read_text(
            encoding="utf-8"
        ).strip()

        if key:
            return key

    try:
        key = str(
            st.secrets.get(
                "GEMINI_API_KEY",
                "",
            )
        ).strip()

        if key:
            return key

    except Exception:
        pass

    key = os.getenv(
        "GEMINI_API_KEY",
        "",
    ).strip()

    if key:
        return key

    raise RuntimeError(
        "Gemini API key not found. "
        "Put your API key in "
        ".streamlit\\gemini_api_key.txt"
    )


def get_gemini_client():
    return genai.Client(
        api_key=get_gemini_api_key()
    )


def get_available_models(client):

    models = []

    try:
        for model in client.models.list():

            name = getattr(
                model,
                "name",
                "",
            )

            if not name:
                continue

            name = str(name)

            clean_name = name.replace(
                "models/",
                "",
            )

            supported = getattr(
                model,
                "supported_actions",
                None,
            )

            if supported:

                supported_text = str(
                    supported
                ).lower()

                if (
                    "generatecontent"
                    not in supported_text
                    and "generate_content"
                    not in supported_text
                ):
                    continue

            models.append(clean_name)

    except Exception:
        models = []

    if not models:

        return [
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash-lite",
            "gemini-2.5-flash-lite",
            "gemini-3.6-flash",
        ]

    def score(name):

        lowered = name.lower()

        score_value = 0

        if "flash-lite" in lowered:
            score_value += 100

        if "flash" in lowered:
            score_value += 50

        if "pro" in lowered:
            score_value -= 20

        if "embedding" in lowered:
            score_value -= 1000

        if "image" in lowered:
            score_value -= 1000

        if "tts" in lowered:
            score_value -= 1000

        if "audio" in lowered:
            score_value -= 1000

        return score_value

    models.sort(
        key=score,
        reverse=True,
    )

    return models


def call_gemini_json(
    system_prompt,
    user_prompt,
):

    client = get_gemini_client()

    models = get_available_models(
        client
    )

    last_error = None

    models = models[:8]

    for model_name in models:

        for attempt in range(3):

            try:

                response = (
                    client.models.generate_content(
                        model=model_name,
                        contents=(
                            system_prompt
                            + "\n\n"
                            + user_prompt
                        ),
                        config={
                            "temperature": 0,
                            "response_mime_type": (
                                "application/json"
                            ),
                        },
                    )
                )

                result_text = getattr(
                    response,
                    "text",
                    None,
                )

                if not result_text:
                    raise RuntimeError(
                        f"{model_name} returned "
                        "an empty response."
                    )

                return json.loads(
                    result_text
                )

            except Exception as exc:

                last_error = exc

                error_text = str(
                    exc
                ).lower()

                temporary_error = any(
                    phrase in error_text
                    for phrase in [
                        "503",
                        "unavailable",
                        "high demand",
                        "429",
                        "rate limit",
                        "resource exhausted",
                        "overloaded",
                        "timeout",
                        "deadline",
                        "temporarily",
                    ]
                )

                model_error = any(
                    phrase in error_text
                    for phrase in [
                        "404",
                        "not found",
                        "no longer available",
                        "unsupported",
                        "shut down",
                    ]
                )

                if temporary_error:

                    time.sleep(
                        2 ** attempt
                    )

                    continue

                if model_error:
                    break

                break

    raise RuntimeError(
        "All available Gemini models failed. "
        f"Last error: {last_error}"
    )


# ============================================================
# DYNAMIC PROJECT COMPONENT DETECTION
# ============================================================

def analyze_project_book(text):

    system_prompt = """
You are analyzing a Community Service Project book.

Your task is to identify the ACTUAL project components
from the supplied document.

STRICT RULES:

1. Use ONLY the supplied CSP project-book content.
2. Do not assume the project domain.
3. Do not use a predefined component list.
4. Do not reuse components from another project.
5. Generate component names yourself from the actual book.
6. Components must represent substantive project activities,
   interventions, technical tasks, community activities,
   implementation activities, training/awareness activities,
   maintenance activities, or clearly addressed problem/solution
   areas.
7. Ignore acknowledgements, certificates and references unless
   they contain actual project activities.
8. Do not create a component merely because a word appears once.
9. Do not fabricate information.
10. Aim for 3 to 5 distinct components ONLY when the book
    genuinely supports them.
11. If the book supports fewer than 3, return fewer.
12. Every component MUST contain evidence from the book.
13. Page numbers must come from [PAGE N] markers.
14. Generate concise, project-specific component names.
15. The component name does NOT need to be an exact sentence
    from the book, but its meaning must be directly supported
    by the book.

Return JSON only:

{
  "project_title": "string",
  "components": [
    {
      "name": "string",
      "evidence": [
        {
          "page": 1,
          "quote": "short supporting quote"
        }
      ]
    }
  ]
}
"""

    max_chars = 80000

    if len(text) <= max_chars:

        result = call_gemini_json(
            system_prompt,
            (
                "Analyze this complete uploaded CSP "
                "project book:\n\n"
                + text
            ),
        )

    else:

        chunk_size = 30000

        chunks = [
            text[i:i + chunk_size]
            for i in range(
                0,
                len(text),
                chunk_size,
            )
        ]

        candidates = []

        for index, chunk in enumerate(
            chunks,
            start=1,
        ):

            prompt = f"""
Analyze this part of the uploaded CSP project book.

Find candidate project components supported by this
document section.

Do not invent components.

Return JSON only:

{{
  "candidates": [
    {{
      "name": "string",
      "evidence": [
        {{
          "page": 1,
          "quote": "short supporting quote"
        }}
      ]
    }}
  ]
}}

This is chunk {index} of {len(chunks)}.

DOCUMENT:
{chunk}
"""

            candidates.append(
                call_gemini_json(
                    system_prompt,
                    prompt,
                )
            )

        synthesis_prompt = """
Combine the candidate components from the uploaded
CSP project book.

STRICT RULES:

- Use only the evidence supplied below.
- Do not use a predefined component list.
- Merge duplicate/overlapping candidates.
- Generate concise project-specific names.
- Aim for 3 to 5 only if supported.
- Do not fabricate components.
- Preserve supporting page numbers and quotes.

Return JSON only:

{
  "project_title": "string",
  "components": [
    {
      "name": "string",
      "evidence": [
        {
          "page": 1,
          "quote": "short supporting quote"
        }
      ]
    }
  ]
}

CANDIDATES:
""" + json.dumps(
            candidates,
            ensure_ascii=False,
        )

        result = call_gemini_json(
            system_prompt,
            synthesis_prompt,
        )

    components = []
    seen = set()

    for item in result.get(
        "components",
        [],
    ):

        if not isinstance(
            item,
            dict,
        ):
            continue

        name = clean_text(
            str(
                item.get(
                    "name",
                    "",
                )
            )
        )

        if not name:
            continue

        evidence = []

        for evidence_item in item.get(
            "evidence",
            [],
        ):

            if not isinstance(
                evidence_item,
                dict,
            ):
                continue

            quote = clean_text(
                str(
                    evidence_item.get(
                        "quote",
                        "",
                    )
                )
            )

            if not quote:
                continue

            page = evidence_item.get(
                "page"
            )

            try:
                page = int(page)
            except (
                TypeError,
                ValueError,
            ):
                page = None

            evidence.append(
                {
                    "page": page,
                    "quote": quote[:500],
                }
            )

        if not evidence:
            continue

        key = name.casefold()

        if key in seen:
            continue

        seen.add(key)

        components.append(
            {
                "name": name[:160],
                "evidence": evidence[:5],
            }
        )

    return {
        "project_title": (
            clean_text(
                str(
                    result.get(
                        "project_title",
                        "",
                    )
                )
            )[:180]
            or extract_title(text)
        ),
        "components": components[:5],
    }


# ============================================================
# FIXED CO -> PO/PSO MATRIX
# ============================================================

def map_co_matrix():

    return [
        [
            "1", "3", "-", "1", "1",
            "3", "2", "2", "2", "-",
            "1", "1", "-", "1",
        ],
        [
            "3", "2", "2", "1", "3",
            "2", "1", "1", "1", "-",
            "1", "3", "2", "2",
        ],
        [
            "2", "3", "2", "3", "2",
            "2", "-", "1", "1", "1",
            "2", "2", "2", "1",
        ],
        [
            "-", "1", "1", "-", "1",
            "3", "3", "3", "3", "1",
            "2", "1", "1", "-",
        ],
        [
            "1", "2", "1", "1", "2",
            "1", "1", "2", "3", "2",
            "3", "1", "1", "1",
        ],
    ]


# ============================================================
# DYNAMIC COMPONENT -> SDG MAPPING
# ============================================================

def map_sdg_components(
    component_objects,
    project_text,
):

    component_names = [
        item["name"]
        for item in component_objects
        if isinstance(item, dict)
        and item.get("name")
    ]

    if not component_names:
        return []

    sdg_catalogue = "\n".join(
        [
            f"SDG {number}: {description}"
            for number, description
            in SDGS.items()
        ]
    )

    evidence_text = []

    for item in component_objects:

        evidence_text.append(
            f"COMPONENT: {item['name']}"
        )

        for evidence in item.get(
            "evidence",
            [],
        ):

            page = evidence.get(
                "page"
            )

            quote = evidence.get(
                "quote",
                "",
            )

            evidence_text.append(
                f"Page {page}: {quote}"
            )

    system_prompt = """
You are an evidence-grounded SDG mapping analyst.

Map the supplied project components to the fixed SDG 1-17
catalogue.

STRICT RULES:

1. Use only the supplied CSP project-book evidence.
2. Do not invent project activities.
3. Do not invent SDGs.
4. Use only SDGs 1 through 17 from the supplied catalogue.
5. Assign an SDG only when there is a meaningful relationship.
6. Strength:
   3 = direct/high contribution
   2 = moderate contribution
   1 = limited but defensible contribution
7. Do not assign an SDG merely to fill a minimum number.
8. Aim for at least 3 SDGs only if the document genuinely
   supports at least 3.
9. If fewer are supported, return fewer.
10. Every mapping reason must be evidence-based.

Return JSON only:

{
  "mappings": [
    {
      "component": "exact component name",
      "sdgs": [
        {
          "number": 1,
          "strength": 1,
          "reason": "brief evidence-based reason"
        }
      ]
    }
  ]
}
"""

    book_text = project_text

    if len(book_text) > 60000:
        book_text = book_text[:60000]

    user_prompt = f"""
FIXED SDG CATALOGUE:

{sdg_catalogue}

PROJECT COMPONENTS:

{json.dumps(
    component_names,
    ensure_ascii=False,
    indent=2,
)}

COMPONENT EVIDENCE:

{chr(10).join(evidence_text)}

UPLOADED CSP PROJECT BOOK:

{book_text}
"""

    result = call_gemini_json(
        system_prompt,
        user_prompt,
    )

    valid_names = set(
        component_names
    )

    rows = []

    for mapping in result.get(
        "mappings",
        [],
    ):

        if not isinstance(
            mapping,
            dict,
        ):
            continue

        component = clean_text(
            str(
                mapping.get(
                    "component",
                    "",
                )
            )
        )

        if component not in valid_names:
            continue

        values = {}

        for sdg in mapping.get(
            "sdgs",
            [],
        ):

            if not isinstance(
                sdg,
                dict,
            ):
                continue

            try:

                number = int(
                    sdg.get(
                        "number"
                    )
                )

                strength = int(
                    sdg.get(
                        "strength"
                    )
                )

            except (
                TypeError,
                ValueError,
            ):
                continue

            if (
                number in SDGS
                and strength in {1, 2, 3}
            ):

                values[number] = str(
                    strength
                )

        if values:

            rows.append(
                (
                    component,
                    values,
                )
            )

    row_map = dict(rows)

    return [
        (
            component,
            row_map[component],
        )
        for component in component_names
        if component in row_map
    ]


# ============================================================
# REPORTLAB
# ============================================================

def P(text, style):

    return Paragraph(
        str(text),
        style,
    )


def build_pdf(
    project_title,
    co_matrix,
    sdg_rows,
):

    buffer = io.BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CSPTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=15,
        leading=18,
        spaceAfter=8,
    )

    heading_style = ParagraphStyle(
        "CSPHeading",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        spaceBefore=6,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "CSPBody",
        parent=styles["BodyText"],
        fontSize=8.5,
        leading=11,
    )

    small_style = ParagraphStyle(
        "CSPSmall",
        parent=body_style,
        fontSize=7,
        leading=9,
    )

    story = []

    story.append(
        P(
            "CO-PO-PSO & WK-PO-PSO Mapping",
            title_style,
        )
    )

    story.append(
        P(
            project_title,
            body_style,
        )
    )

    story.append(
        Spacer(1, 6)
    )

    # ========================================================
    # SECTION 1
    # ========================================================

    story.append(
        P(
            "1) Course Outcomes:",
            heading_style,
        )
    )

    data = [
        [
            P("CO No.", small_style),
            P("Course Outcome", small_style),
            P("Bloom's Level", small_style),
        ]
    ]

    for code, description, bloom in COS:

        data.append(
            [
                P(code, small_style),
                P(description, small_style),
                P(bloom, small_style),
            ]
        )

    table = Table(
        data,
        colWidths=[
            18 * mm,
            126 * mm,
            35 * mm,
        ],
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    colors.black,
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.whitesmoke,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, 0),
                    "CENTER",
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
            ]
        )
    )

    story.append(table)

    story.append(
        Spacer(1, 8)
    )

    # ========================================================
    # SECTION 2
    # ========================================================

    story.append(
        P(
            "2) COs Vs POs and PSOs:",
            heading_style,
        )
    )

    section2_data = [
        [P("CO", small_style)]
        + [
            P(header, small_style)
            for header in HEADERS
        ]
    ]

    for index, (co, _, _) in enumerate(
        COS
    ):

        row = co_matrix[index]

        if len(row) != len(HEADERS):
            raise ValueError(
                f"CO matrix row {index + 1} "
                f"has {len(row)} values; "
                f"{len(HEADERS)} required."
            )

        section2_data.append(
            [P(co, small_style)]
            + [
                P(value, small_style)
                for value in row
            ]
        )

    table = Table(
        section2_data,
        colWidths=[
            14 * mm
        ] + [
            12.2 * mm
        ] * 14,
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.black,
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.whitesmoke,
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    story.append(table)

    story.append(
        Spacer(1, 5)
    )

    story.append(
        P(
            "Scale: 3 = High    2 = Medium    "
            "1 = Low    - = No mapping",
            small_style,
        )
    )

    story.append(
        PageBreak()
    )

    # ========================================================
    # SECTION 3
    # ========================================================

    story.append(
        P(
            "3) Knowledge and Attitude Profile Vs "
            "Program Outcomes and Program Specific Outcomes",
            heading_style,
        )
    )

    section3_data = [
        [P("", small_style)]
        + [
            P(header, small_style)
            for header in HEADERS
        ]
    ]

    for index, (wk, _) in enumerate(
        WKS
    ):

        row = FIXED_WK_MATRIX[index]

        if len(row) != len(HEADERS):
            raise ValueError(
                f"WK matrix row {index + 1} "
                f"has {len(row)} values; "
                f"{len(HEADERS)} required."
            )

        section3_data.append(
            [P(wk, small_style)]
            + [
                P(value, small_style)
                for value in row
            ]
        )

    table = Table(
        section3_data,
        colWidths=[
            15 * mm
        ] + [
            12.1 * mm
        ] * 14,
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.black,
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.whitesmoke,
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    story.append(table)

    story.append(
        Spacer(1, 5)
    )

    story.append(
        P(
            "Scale: 3 = High    2 = Medium    "
            "1 = Low",
            small_style,
        )
    )

    story.append(
        PageBreak()
    )

    # ========================================================
    # SECTION 4
    # ========================================================

    story.append(
        P(
            "4) SDGs Vs Community Service "
            "Project Components:",
            heading_style,
        )
    )

    if sdg_rows:

        matched_sdgs = sorted(
            {
                number
                for _, values in sdg_rows
                for number in values
                if number in SDGS
            }
        )

        if matched_sdgs:

            section4_data = [
                [
                    P(
                        "Project Component",
                        small_style,
                    )
                ]
                + [
                    P(
                        f"SDG {number}",
                        small_style,
                    )
                    for number in matched_sdgs
                ]
            ]

            for component, values in sdg_rows:

                row = [
                    P(
                        component,
                        small_style,
                    )
                ]

                for number in matched_sdgs:

                    # ====================================================
                    # ONLY CHANGE:
                    # Missing Section 4 values are now "3" instead of "-"
                    # ====================================================

                    row.append(
                        P(
                            values.get(
                                number,
                                "3",
                            ),
                            small_style,
                        )
                    )

                section4_data.append(row)

            component_width = 68 * mm

            available_width = (
                A4[0] - 24 * mm
            )

            remaining_width = (
                available_width
                - component_width
            )

            sdg_width = (
                remaining_width
                / len(matched_sdgs)
            )

            table = Table(
                section4_data,
                colWidths=[
                    component_width
                ] + [
                    sdg_width
                ] * len(matched_sdgs),
                repeatRows=1,
            )

            table.setStyle(
                TableStyle(
                    [
                        (
                            "GRID",
                            (0, 0),
                            (-1, -1),
                            0.5,
                            colors.black,
                        ),
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            colors.whitesmoke,
                        ),
                        (
                            "FONTNAME",
                            (0, 0),
                            (-1, 0),
                            "Helvetica-Bold",
                        ),
                        (
                            "ALIGN",
                            (0, 0),
                            (-1, -1),
                            "CENTER",
                        ),
                        (
                            "ALIGN",
                            (0, 1),
                            (0, -1),
                            "LEFT",
                        ),
                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "MIDDLE",
                        ),
                        (
                            "FONTSIZE",
                            (0, 0),
                            (-1, -1),
                            7,
                        ),
                        (
                            "LEFTPADDING",
                            (0, 0),
                            (-1, -1),
                            4,
                        ),
                        (
                            "RIGHTPADDING",
                            (0, 0),
                            (-1, -1),
                            4,
                        ),
                        (
                            "TOPPADDING",
                            (0, 0),
                            (-1, -1),
                            4,
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, -1),
                            4,
                        ),
                    ]
                )
            )

            story.append(table)

            story.append(
                Spacer(1, 6)
            )

            story.append(
                P(
                    "Mapping scale: 3 = High    "
                    "2 = Medium    1 = Low",
                    small_style,
                )
            )

        else:

            story.append(
                P(
                    "No defensible SDG relationship "
                    "was found from the uploaded project book.",
                    body_style,
                )
            )

    else:

        story.append(
            P(
                "No defensible SDG relationship "
                "was found from the uploaded project book.",
                body_style,
            )
        )

    document.build(story)

    buffer.seek(0)

    return buffer.getvalue()


# ============================================================
# STREAMLIT APPLICATION
# ============================================================

st.title(
    "📘 CSP Outcome Mapping Generator"
)

st.caption(
    "Upload one Community Service Project book "
    "→ AI reads the actual book "
    "→ detects project components from the book "
    "→ maps them to SDGs "
    "→ generates Sections 1–4 as a PDF."
)

uploaded = st.file_uploader(
    "Upload your CSP Project Book (PDF)",
    type=["pdf"],
)


if uploaded:

    # --------------------------------------------------------
    # EXTRACT PDF
    # --------------------------------------------------------

    with st.spinner(
        "Extracting the CSP project book..."
    ):

        text = extract_text(
            uploaded
        )

    if not text.strip():

        st.error(
            "No selectable text was found in this PDF."
        )

        st.info(
            "This application requires a text-readable PDF."
        )

        st.stop()

    cleaned_text = clean_text(
        text
    )

    # --------------------------------------------------------
    # AI COMPONENT DETECTION
    # --------------------------------------------------------

    try:

        with st.spinner(
            "AI is reading the complete CSP book "
            "and identifying actual project components..."
        ):

            analysis = analyze_project_book(
                text
            )

    except Exception as exc:

        st.error(
            "Project-book AI analysis failed."
        )

        st.code(
            str(exc)
        )

        st.info(
            "Check your Gemini API key and Gemini API access."
        )

        st.stop()

    project_title = (
        analysis.get(
            "project_title"
        )
        or extract_title(text)
    )

    component_objects = (
        analysis.get(
            "components",
            [],
        )
    )

    components = [
        item["name"]
        for item in component_objects
        if isinstance(item, dict)
        and item.get("name")
    ]

    if not components:

        st.error(
            "The AI could not find a substantive "
            "project component supported by the uploaded book."
        )

        st.stop()

    # --------------------------------------------------------
    # FIXED SECTION 2
    # --------------------------------------------------------

    co_matrix = map_co_matrix()

    # --------------------------------------------------------
    # DYNAMIC SDG MAPPING
    # --------------------------------------------------------

    try:

        with st.spinner(
            "Mapping the actual project components "
            "to relevant SDGs..."
        ):

            sdg_rows = map_sdg_components(
                component_objects,
                cleaned_text,
            )

    except Exception as exc:

        st.error(
            "SDG mapping failed."
        )

        st.code(
            str(exc)
        )

        st.stop()

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    st.success(
        f"PDF extracted successfully. "
        f"{len(text):,} characters analyzed. "
        f"{len(components)} project components detected."
    )

    # --------------------------------------------------------
    # PROJECT COMPONENT EVIDENCE
    # --------------------------------------------------------

    st.subheader(
        "Project Components Detected From CSP Book"
    )

    st.write(
        "These components were generated from the uploaded "
        "CSP project book. No predefined project-component "
        "list is used."
    )

    for number, component in enumerate(
        components,
        start=1,
    ):

        st.write(
            f"**{number}. {component}**"
        )

    with st.expander(
        "🔎 Show evidence used for component detection"
    ):

        for item in component_objects:

            st.markdown(
                f"### {item['name']}"
            )

            for evidence in item.get(
                "evidence",
                [],
            ):

                page = evidence.get(
                    "page"
                )

                quote = evidence.get(
                    "quote",
                    "",
                )

                if page:

                    st.write(
                        f'Page {page}: "{quote}"'
                    )

                else:

                    st.write(
                        f'"{quote}"'
                    )

    # --------------------------------------------------------
    # OPTIONAL COMPONENT EDITING
    # --------------------------------------------------------

    st.subheader(
        "Section 4 Components"
    )

    edited_components_text = st.text_area(
        "One component per line. "
        "Only edit if you need to correct the AI-generated labels.",
        value="\n".join(
            components
        ),
        height=160,
    )

    edited_components = [
        value.strip()
        for value in edited_components_text.splitlines()
        if value.strip()
    ]

    if st.button(
        "🔄 Re-map SDGs for edited components"
    ):

        if not edited_components:

            st.warning(
                "Enter at least one component."
            )

        else:

            edited_objects = [
                {
                    "name": name,
                    "evidence": [],
                }
                for name in edited_components
            ]

            try:

                with st.spinner(
                    "Checking edited components "
                    "against the uploaded CSP book..."
                ):

                    new_rows = map_sdg_components(
                        edited_objects,
                        cleaned_text,
                    )

                st.session_state[
                    "active_components"
                ] = edited_components

                st.session_state[
                    "active_sdg_rows"
                ] = new_rows

                st.success(
                    "SDG mapping updated."
                )

            except Exception as exc:

                st.error(
                    f"SDG remapping failed: {exc}"
                )

    # --------------------------------------------------------
    # ACTIVE DATA
    # --------------------------------------------------------

    active_components = st.session_state.get(
        "active_components",
        components,
    )

    active_sdg_rows = st.session_state.get(
        "active_sdg_rows",
        sdg_rows,
    )

    # --------------------------------------------------------
    # SECTION 2 PREVIEW
    # --------------------------------------------------------

    st.subheader(
        "Section 2 — CO → PO/PSO Mapping"
    )

    section2_preview = {
        "CO": [
            item[0]
            for item in COS
        ]
    }

    for column_index, header in enumerate(
        HEADERS
    ):

        section2_preview[
            header
        ] = [
            co_matrix[row_index][column_index]
            for row_index in range(
                len(COS)
            )
        ]

    st.dataframe(
        pd.DataFrame(
            section2_preview
        ),
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # SECTION 3 PREVIEW
    # --------------------------------------------------------

    st.subheader(
        "Section 3 — WK → PO/PSO Mapping"
    )

    section3_preview = {
        "WK": [
            item[0]
            for item in WKS
        ]
    }

    for column_index, header in enumerate(
        HEADERS
    ):

        section3_preview[
            header
        ] = [
            FIXED_WK_MATRIX[row_index][column_index]
            for row_index in range(
                len(WKS)
            )
        ]

    st.dataframe(
        pd.DataFrame(
            section3_preview
        ),
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # SECTION 4 PREVIEW
    # --------------------------------------------------------

    st.subheader(
        "Section 4 — Project Components → SDGs"
    )

    matched_sdgs = sorted(
        {
            number
            for _, values in active_sdg_rows
            for number in values
            if number in SDGS
        }
    )

    if active_sdg_rows and matched_sdgs:

        preview_rows = []

        for component, values in (
            active_sdg_rows
        ):

            row = {
                "Project Component": component
            }

            for number in matched_sdgs:

                # ====================================================
                # ONLY CHANGE:
                # Missing Section 4 values are now "3" instead of "-"
                # ====================================================

                row[
                    f"SDG {number}"
                ] = values.get(
                    number,
                    "3",
                )

            preview_rows.append(
                row
            )

        st.dataframe(
            pd.DataFrame(
                preview_rows
            ),
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.warning(
            "No defensible SDG relationship "
            "was found from the uploaded CSP book."
        )

    # --------------------------------------------------------
    # FINAL PDF
    # --------------------------------------------------------

    st.subheader(
        "Generate Final PDF"
    )

    if st.button(
        "📄 Generate Final CSP PDF",
        type="primary",
    ):

        try:

            pdf_bytes = build_pdf(
                project_title,
                co_matrix,
                active_sdg_rows,
            )

            st.success(
                "Final CSP PDF generated successfully."
            )

            st.download_button(
                label="⬇️ Download Final CSP PDF",
                data=pdf_bytes,
                file_name=(
                    "CSP_CO_PO_PSO_WK_SDG_Mapping.pdf"
                ),
                mime="application/pdf",
            )

        except Exception as exc:

            st.error(
                "PDF generation failed."
            )

            st.code(
                str(exc)
            )

else:

    st.info(
        "Upload your CSP project-book PDF to begin."
    )
