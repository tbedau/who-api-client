import html
import re
from html.parser import HTMLParser
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class _TableHTMLParser(HTMLParser):
    """Parse HTML table into a grid of cells, handling colspan and rowspan."""

    def __init__(self):
        super().__init__()
        self.rows: list[list[str]] = []
        self._current_row: list[tuple[str, int, int]] = []  # (text, colspan, rowspan)
        self._current_text: list[str] = []
        self._in_cell = False
        self._colspan = 1
        self._rowspan = 1

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in ("td", "th"):
            self._in_cell = True
            self._current_text = []
            attr_dict = dict(attrs)
            self._colspan = int(attr_dict.get("colspan", "1"))
            self._rowspan = int(attr_dict.get("rowspan", "1"))
        elif tag == "tr":
            self._current_row = []
        elif tag == "br" and self._in_cell:
            self._current_text.append(" ")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in ("td", "th"):
            text = "".join(self._current_text).strip()
            # Collapse whitespace
            text = re.sub(r"\s+", " ", text)
            self._current_row.append((text, self._colspan, self._rowspan))
            self._in_cell = False
        elif tag == "tr":
            self.rows.append(list(self._current_row))

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._current_text.append(data)

    def handle_entityref(self, name: str) -> None:
        if self._in_cell:
            self._current_text.append(html.unescape(f"&{name};"))

    def handle_charref(self, name: str) -> None:
        if self._in_cell:
            self._current_text.append(html.unescape(f"&#{name};"))


def _html_table_to_markdown(html_str: str) -> str:
    """Convert an HTML table string to a markdown table.

    Handles colspan (expanding cells across columns) and rowspan (filling cells
    into subsequent rows). Strips all inline styling and MS Word attributes.
    """
    if not html_str or "<table" not in html_str.lower():
        return ""

    # Decode any HTML entities in the raw string first
    html_str = html.unescape(html_str)

    parser = _TableHTMLParser()
    parser.feed(html_str)

    if not parser.rows:
        return ""

    # Phase 1: Expand colspan/rowspan into a full grid
    # First pass: determine total column count
    max_cols = 0
    for row in parser.rows:
        col_count = sum(colspan for _, colspan, _ in row)
        if col_count > max_cols:
            max_cols = col_count

    if max_cols == 0:
        return ""

    # Build the expanded grid, handling rowspan carry-overs
    grid: list[list[str]] = []
    # Track pending rowspans: rowspan_carry[col] = (text, remaining_rows)
    rowspan_carry: dict[int, tuple[str, int]] = {}

    for row in parser.rows:
        grid_row = [""] * max_cols
        col_idx = 0
        cell_idx = 0

        while col_idx < max_cols:
            # Fill from rowspan carry-over
            if col_idx in rowspan_carry:
                text, remaining = rowspan_carry[col_idx]
                grid_row[col_idx] = text
                if remaining > 1:
                    rowspan_carry[col_idx] = (text, remaining - 1)
                else:
                    del rowspan_carry[col_idx]
                col_idx += 1
                continue

            # Fill from current row's cells
            if cell_idx < len(row):
                text, colspan, rowspan = row[cell_idx]
                cell_idx += 1
                for c in range(colspan):
                    if col_idx + c < max_cols:
                        grid_row[col_idx + c] = text if c == 0 else ""
                # Register rowspan for subsequent rows
                if rowspan > 1:
                    for c in range(colspan):
                        if col_idx + c < max_cols:
                            rowspan_carry[col_idx + c] = (
                                text if c == 0 else "",
                                rowspan - 1,
                            )
                col_idx += colspan
            else:
                col_idx += 1

        grid.append(grid_row)

    # Drain any remaining rowspan carries
    while rowspan_carry:
        grid_row = [""] * max_cols
        next_carry: dict[int, tuple[str, int]] = {}
        for col_idx, (text, remaining) in rowspan_carry.items():
            grid_row[col_idx] = text
            if remaining > 1:
                next_carry[col_idx] = (text, remaining - 1)
        grid.append(grid_row)
        rowspan_carry = next_carry

    if not grid:
        return ""

    # Phase 2: Calculate column widths and render markdown
    col_widths = [3] * max_cols  # minimum width of 3 for "---"
    for row in grid:
        for i, cell in enumerate(row):
            if len(cell) > col_widths[i]:
                col_widths[i] = len(cell)

    def format_row(cells: list[str]) -> str:
        padded = [cell.ljust(col_widths[i]) for i, cell in enumerate(cells)]
        return "| " + " | ".join(padded) + " |"

    lines = []
    # Header row
    lines.append(format_row(grid[0]))
    # Separator
    lines.append("| " + " | ".join("-" * w for w in col_widths) + " |")
    # Data rows
    for row in grid[1:]:
        lines.append(format_row(row))

    return "\n".join(lines)


class LoginRequest(BaseModel):
    """Login request payload"""

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )

    Email: EmailStr = Field(alias="email")
    Password: str = Field(alias="password")
    Path: str = Field(default="https://tumourclassification.iarc.who.int")


class LoginResponse(BaseModel):
    """Login response data"""

    success: bool
    token: str | None = None
    message: str | None = None


class Book(BaseModel):
    """Individual book information"""

    pkbookId: int
    bookid: int
    bookTitle: str
    bookThumbnail: str
    sequence: int
    series: str
    revision: str
    fkseriesId: int
    isActive: bool


class BookSeries(BaseModel):
    """WHO Book Series information"""

    series: str
    pageHeading: str
    tabFontColor: str
    tabBorderColor: str
    onSelectTabBackgroundColor: str
    onSelectTabFontColor: str
    contentHeadingFontColor: str
    books: list[Book]


class BookSeriesResponse(BaseModel):
    """Response containing list of book series"""

    series: list[BookSeries]
    count: int


class BookColors(BaseModel):
    """Book color configuration and series information for UI theming"""

    pkseriesId: int
    seriesName: str
    sequence: int
    tabFontColor: str
    tabBorderColor: str
    onSelectTabBackgroundColor: str
    onSelectTabFontColor: str
    contentHeadingFontColor: str
    pageHeading: str


class ChapterAncestor(BaseModel):
    """Chapter ancestor information (without nested structure)"""

    pkchapterIndex: int
    chapterId: int
    bookId: int
    chapterNumber: str
    chapterTitle: str
    chapterPosition: int
    headingType: int
    chapterLevel: int


class Chapter(BaseModel):
    """Chapter information with nested structure"""

    pkchapterIndex: int
    chapterId: int
    bookId: int
    chapterNumber: str
    chapterTitle: str
    chapterPosition: int
    headingType: int
    chapterLevel: int
    chapNum: int
    chapters: list["Chapter"] | None = None

    @property
    def sub_chapters(self) -> list["Chapter"]:
        """Get sub-chapters, returning empty list if None"""
        return self.chapters or []


class Contribution(BaseModel):
    """Individual contribution content"""

    pkcontributionId: int
    bookId: int
    chapterId: int
    headingId: int
    headingText: str
    timestamp: str


class ChapterContent(BaseModel):
    """Chapter content with headings and contributions"""

    pkheadingid: int
    bookid: int
    headingType: int
    headingTitle: str
    headingPosition: int
    headingid: int
    contributions: list[Contribution]
    booknotes: list[Any]
    numberofBooknote: int

    @property
    def content_text(self) -> str:
        """Get combined content text from all contributions"""
        return "\n".join(contrib.headingText for contrib in self.contributions)

    @property
    def clean_content_text(self) -> str:
        """Get combined content text with HTML tags removed and entities decoded"""
        text = self.content_text
        # Strip HTML tags
        clean_text = re.sub("<[^<]+?>", "", text).strip()
        # Decode HTML entities (like &nbsp;, &ndash;, etc.)
        clean_text = html.unescape(clean_text)
        # Clean up extra whitespace and normalize spaces
        clean_text = re.sub(r"\s+", " ", clean_text)
        # Remove non-breaking spaces that might remain
        clean_text = clean_text.replace("\u00a0", " ")
        return clean_text.strip()


class Attachment(BaseModel):
    """Chapter attachment (image, table, etc.)"""

    pkattachmentId: int
    bookid: int
    chapterId: int
    fileId: int
    type: str  # "Figure", "Table", etc.
    diagnosis: str
    title: str
    legend: str
    source: str
    copyright: str
    tablehtml: str
    imageUrl: str | None = None
    thumbnail: str | None = None

    @property
    def is_figure(self) -> bool:
        """Check if this attachment is a regular figure (not WSI)"""
        return self.type.lower() == "figure" and self.imageUrl is not None

    @property
    def is_wsi(self) -> bool:
        """Check if this attachment is a whole slide image"""
        return self.type.upper() == "WSI" and self.imageUrl is not None

    @property
    def is_image(self) -> bool:
        """Check if this attachment is an image (figure or WSI)"""
        return self.is_figure or self.is_wsi

    @property
    def is_table(self) -> bool:
        """Check if this attachment is a table"""
        return self.type.lower() == "table" and bool(self.tablehtml)

    @property
    def image_type(self) -> str | None:
        """Get the image type: 'figure', 'wsi', 'table', or None"""
        if self.is_figure:
            return "figure"
        elif self.is_wsi:
            return "wsi"
        elif self.is_table:
            return "table"
        return None

    @property
    def clean_diagnosis(self) -> str:
        """Get diagnosis with HTML tags removed and entities decoded"""
        text = self.diagnosis
        # Strip HTML tags
        clean_text = re.sub("<[^<]+?>", "", text).strip()
        # Decode HTML entities
        clean_text = html.unescape(clean_text)
        # Clean up extra whitespace
        clean_text = re.sub(r"\s+", " ", clean_text)
        return clean_text.strip()

    @property
    def clean_legend(self) -> str:
        """Get legend with HTML tags removed and entities decoded"""
        text = self.legend
        # Strip HTML tags
        clean_text = re.sub("<[^<]+?>", "", text).strip()
        # Decode HTML entities
        clean_text = html.unescape(clean_text)
        # Clean up extra whitespace
        clean_text = re.sub(r"\s+", " ", clean_text)
        return clean_text.strip()

    @property
    def clean_title(self) -> str:
        """Get title with HTML tags removed and entities decoded"""
        text = self.title
        # Strip HTML tags
        clean_text = re.sub("<[^<]+?>", "", text).strip()
        # Decode HTML entities
        clean_text = html.unescape(clean_text)
        # Clean up extra whitespace
        clean_text = re.sub(r"\s+", " ", clean_text)
        return clean_text.strip()

    @property
    def clean_copyright(self) -> str:
        """Get copyright with HTML tags removed and entities decoded"""
        text = self.copyright
        # Strip HTML tags
        clean_text = re.sub("<[^<]+?>", "", text).strip()
        # Decode HTML entities
        clean_text = html.unescape(clean_text)
        # Clean up extra whitespace
        clean_text = re.sub(r"\s+", " ", clean_text)
        return clean_text.strip()

    @property
    def clean_source(self) -> str:
        """Get source with HTML tags removed and entities decoded"""

        text = self.source
        # Strip HTML tags
        clean_text = re.sub("<[^<]+?>", "", text).strip()
        # Decode HTML entities
        clean_text = html.unescape(clean_text)
        # Clean up extra whitespace
        clean_text = re.sub(r"\s+", " ", clean_text)
        return clean_text.strip()

    @property
    def table_markdown(self) -> str:
        """Convert tablehtml to a markdown table. Returns empty string for non-table attachments."""
        if not self.is_table:
            return ""
        return _html_table_to_markdown(self.tablehtml)


class Contributor(BaseModel):
    """Individual contributor information"""

    contributorid: int
    lastname: str
    firstname: str
    initials: str
    email: str
    roleid: int
    position: int


class Assignment(BaseModel):
    """Role assignment with contributors for a book/chapter"""

    pkroleId: int
    bookId: str
    roleid: int
    roleTitle: str
    contributors: list[Contributor]


class UserDetails(BaseModel):
    """User profile and subscription details"""

    pkuserId: int
    subscriptionStartDate: str
    subscriptionEndDate: str
    code: str | None = None
    codeDate: str | None = None
    email: EmailStr
    name: str
    passwordAttempted: int
    subscriptionEndsin: str
    isRenewal: bool
    subscriptionRenewalUrl: str
    password: str  # Note: This appears to be a hashed password
    title: str
    firstName: str
    lastName: str
    currentPosition: str
    department: str
    institution: str
    institutionAddress: str
    city: str
    country: str
    zipcode: str
    isProfileUpdated: bool
    profileNotUpdatedMessage: str


class FavouriteRequest(BaseModel):
    """Request to check or modify favourite status of a chapter"""

    ChapterId: str
    BookId: str


class AddFavouriteResponse(BaseModel):
    """Response from adding a chapter to favourites"""

    isExist: bool
    message: str


class RemoveFavouriteResponse(BaseModel):
    """Response from removing a chapter from favourites"""

    message: str


class FavouriteChapter(BaseModel):
    """Individual favourite chapter details"""

    pkmyFavouriteId: int
    bookId: int
    chapterId: int
    bookTitle: str | None = None
    chapterTitle: str | None = None
    chapters: list["FavouriteChapter"] | None = None


class FavouriteBook(BaseModel):
    """Book with favourite chapters grouped together"""

    pkmyFavouriteId: int
    bookId: int
    chapterId: int
    bookTitle: str
    chapterTitle: str | None = None
    chapters: list[FavouriteChapter]


class SearchTerm(BaseModel):
    """Individual search term with boolean logic support"""

    priorityUp: bool = False  # Opening parenthesis "("
    prioritydown: bool = False  # Closing parenthesis ")"
    searchText: str
    searchConditionEnum: int  # 0=no operator, 1=AND, 2=OR, 3=NOT


class AdvancedSearchRequest(BaseModel):
    """Advanced search request with boolean logic"""

    bookIds: list[int]
    seachTerms: list[SearchTerm]  # Note: API uses "seach" not "search"
    searchTypeEnums: list[
        int
    ]  # [0]=both text+headings, [1]=text only, [2]=headings only, [1,2]=text+headings
    # Note: Tested behavior - [0] and [1,2] are equivalent (both text+headings),
    # [1] searches text only, [2] searches headings only (true heading-only search).


class SearchResult(BaseModel):
    """Individual search result"""

    bookId: int
    chapterId: int
    headingId: int
    contributorId: int
    title: str
    url: str | None = None
    headingType: int
    searchedString: str | None = None
    ranking: float
    isActive: bool | None = None


class AdvancedSearchResponse(BaseModel):
    """Advanced search response with results"""

    isMoreResults: bool
    results: list[SearchResult]


class SimpleSearchRequest(BaseModel):
    """Simple search request with filter options"""

    BookIds: list[str]  # Note: Simple search uses strings for book IDs
    Search: str
    IsMoreResults: bool = False
    IncludeChapter: bool = True
    IncludeChapterHeading: bool = False
    IncludeChapterContent: bool = False


class SimpleSearchResponse(BaseModel):
    """Simple search response with results"""

    isMoreResults: bool
    results: list[SearchResult]


class APIError(BaseModel):
    """API error response"""

    error: str
    code: int
    details: dict[str, Any] | None = None
