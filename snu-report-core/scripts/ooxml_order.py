"""OOXML 스키마 순서 정리 — Word 호환성 검사·"읽을 수 없는 내용" 경고를 막는다.

pandoc 출력과 후처리로 붙인 속성은 Word가 대체로 읽어 주지만, 스키마 순서가 틀리면
호환성 검사나 다른 뷰어에서 문제가 된다. 저장 직전에 한 번 돌린다.
"""
from __future__ import annotations

from docx.oxml.ns import qn

W = lambda names: [qn("w:" + n) for n in names.split()]  # noqa: E731
M = lambda names: [qn("m:" + n) for n in names.split()]  # noqa: E731

ORDER = {
    qn("w:pPr"): W("pStyle keepNext keepLines pageBreakBefore framePr widowControl numPr suppressLineNumbers pBdr "
                   "shd tabs suppressAutoHyphens kinsoku wordWrap overflowPunct topLinePunct autoSpaceDE autoSpaceDN "
                   "bidi adjustRightInd snapToGrid spacing ind contextualSpacing mirrorIndents suppressOverlap jc "
                   "textDirection textAlignment textboxTightWrap outlineLvl divId cnfStyle rPr sectPr pPrChange"),
    qn("w:rPr"): W("ins del moveFrom moveTo rStyle rFonts b bCs i iCs caps smallCaps strike dstrike outline shadow "
                   "emboss imprint noProof snapToGrid vanish webHidden color spacing w kern position sz szCs "
                   "highlight u effect bdr shd fitText vertAlign rtl cs em lang eastAsianLayout specVanish oMath"),
    qn("w:tblPr"): W("tblStyle tblpPr tblOverlap bidiVisual tblStyleRowBandSize tblStyleColBandSize tblW jc "
                     "tblCellSpacing tblInd tblBorders shd tblLayout tblCellMar tblLook tblCaption tblDescription"),
    qn("w:tcPr"): W("cnfStyle tcW gridSpan hMerge vMerge tcBorders shd noWrap tcMar textDirection tcFitText vAlign "
                    "hideMark"),
    qn("w:style"): W("name aliases basedOn next link autoRedefine hidden uiPriority semiHidden unhideWhenUsed qFormat "
                     "locked personal personalCompose personalReply rsid pPr rPr tblPr trPr tcPr tblStylePr"),
    qn("w:sectPr"): W("headerReference footerReference footnotePr endnotePr type pgSz pgMar paperSrc pgBorders "
                      "lnNumType pgNumType cols formProt vAlign noEndnote titlePg textDirection bidi rtlGutter "
                      "docGrid printerSettings sectPrChange"),
    qn("w:settings"): W("writeProtection view zoom removePersonalInformation removeDateAndTime "
                        "doNotDisplayPageBoundaries displayBackgroundShape printPostScriptOverText "
                        "printFractionalCharacterWidth printFormsData embedTrueTypeFonts embedSystemFonts "
                        "saveSubsetFonts saveFormsData mirrorMargins alignBordersAndEdges bordersDoNotSurroundHeader "
                        "bordersDoNotSurroundFooter gutterAtTop hideSpellingErrors hideGrammaticalErrors "
                        "activeWritingStyle proofState formsDesign attachedTemplate linkStyles stylePaneFormatFilter "
                        "stylePaneSortMethod documentType mailMerge revisionView trackRevisions doNotTrackMoves "
                        "doNotTrackFormatting documentProtection autoFormatOverride styleLockTheme styleLockQFSet "
                        "defaultTabStop autoHyphenation consecutiveHyphenLimit hyphenationZone doNotHyphenateCaps "
                        "showEnvelope summaryLength clickAndTypeStyle defaultTableStyle evenAndOddHeaders "
                        "bookFoldRevPrinting bookFoldPrinting bookFoldPrintingSheets drawingGridHorizontalSpacing "
                        "drawingGridVerticalSpacing displayHorizontalDrawingGridEvery "
                        "displayVerticalDrawingGridEvery doNotUseMarginsForDrawingGridOrigin "
                        "drawingGridHorizontalOrigin drawingGridVerticalOrigin doNotShadeFormData "
                        "noPunctuationKerning characterSpacingControl printTwoOnOne strictFirstAndLastChars "
                        "noLineBreaksAfter noLineBreaksBefore savePreviewPicture doNotValidateAgainstSchema "
                        "saveInvalidXml ignoreMixedContent alwaysShowPlaceholderText doNotDemarcateInvalidXml "
                        "saveXmlDataOnly useXSLTWhenSaving saveThroughXslt showXMLTags alwaysMergeEmptyNamespace "
                        "updateFields hdrShapeDefaults footnotePr endnotePr compat docVars rsids")
                      + M("mathPr")
                      + W("attachedSchema themeFontLang clrSchemeMapping doNotIncludeSubdocsInStats "
                          "doNotAutoCompressPictures forceUpgrade captions readModeInkLockDown smartTagType")
                      + [qn("sl:schemaLibrary")]
                      + W("shapeDefaults doNotEmbedSmartTags decimalSymbol listSeparator"),
    qn("m:dPr"): M("begChr sepChr endChr grow shp ctrlPr"),
    qn("m:mathPr"): M("mathFont brkBin brkBinSub smallFrac dispDef lMargin rMargin defJc preSp postSp interSp intraSp wrapIndent wrapRight intLim naryLim"),
    qn("m:oMathPara"): M("oMathParaPr oMath"),
    qn("m:r"): M("rPr") + W("rPr") + M("t"),
}
ELEMENT_ONLY = set(ORDER) | {qn("w:tblPr"), qn("w:tcPr"), qn("w:trPr")}


def _sort(el, order):
    idx = {t: i for i, t in enumerate(order)}
    kids = list(el)
    keyed = sorted(range(len(kids)), key=lambda k: (idx.get(kids[k].tag, len(order)), k))
    if keyed != list(range(len(kids))):
        for c in kids:
            el.remove(c)
        for k in keyed:
            el.append(kids[k])
        return 1
    return 0


def normalize(root) -> int:
    """root 아래의 알려진 속성 요소를 스키마 순서로 정렬하고 작은 스키마 위반을 고친다."""
    n = 0
    for el in root.iter():
        if el.tag in ELEMENT_ONLY:
            if el.text and el.text.strip():
                el.text = None
            for c in el:
                if c.tail and c.tail.strip():
                    c.tail = None
        order = ORDER.get(el.tag)
        if order:
            n += _sort(el, order)
        if el.tag == qn("w:pgMar"):
            for a, v in (("w:header", "720"), ("w:footer", "720"), ("w:gutter", "0")):
                if el.get(qn(a)) is None:
                    el.set(qn(a), v)
        if el.tag == qn("w:nsid") or el.tag == qn("w:tmpl"):
            v = el.get(qn("w:val"))
            if v and len(v) < 8:
                el.set(qn("w:val"), v.zfill(8).upper())
        if el.tag == qn("m:rPr") and el.find(qn("m:nor")) is not None:   # nor와 sty는 함께 쓸 수 없다
            for s in el.findall(qn("m:sty")):
                el.remove(s)
    return n


def normalize_document(doc) -> int:
    n = normalize(doc.element)
    n += normalize(doc.styles.element)
    n += normalize(doc.settings.element)
    try:
        n += normalize(doc.part.numbering_part.element)
    except Exception:
        pass
    return n
