/**
 * NovelAI tag autocomplete for prompt textareas.
 * Triggers on the current comma-separated token being typed,
 * shows a dropdown of suggestions, and inserts the selected tag.
 * Only active when the NovelAI provider is selected.
 */
const MODEL = "nai-diffusion-3";
const DEBOUNCE_MS = 300;
const MAX_SUGGESTIONS = 10;
let debounceTimer = null;
let activeTextarea = null;
let dropdown = null;
let selectedIndex = -1;
function isNovelAIActive() {
    const provider = document.getElementById("provider");
    return provider?.value === "novelai";
}
/** Extract the token currently being typed (after the last comma). */
function getCurrentToken(textarea) {
    const cursor = textarea.selectionStart ?? 0;
    const text = textarea.value.slice(0, cursor);
    const lastComma = text.lastIndexOf(",");
    const start = lastComma + 1;
    const token = text.slice(start).trimStart();
    return { token, start: start + (text.slice(start).length - token.length) };
}
function removeDropdown() {
    dropdown?.remove();
    dropdown = null;
    selectedIndex = -1;
}
function buildDropdown(suggestions, textarea) {
    removeDropdown();
    if (suggestions.length === 0)
        return;
    dropdown = document.createElement("ul");
    dropdown.className = "nai-tag-suggestions";
    suggestions.slice(0, MAX_SUGGESTIONS).forEach((s, i) => {
        const li = document.createElement("li");
        li.className = "nai-tag-suggestion-item";
        li.dataset.tag = s.tag;
        const tagSpan = document.createElement("span");
        tagSpan.className = "nai-tag-name";
        tagSpan.textContent = s.tag;
        const countSpan = document.createElement("span");
        countSpan.className = "nai-tag-count";
        countSpan.textContent = s.count > 0 ? s.count.toLocaleString() : "";
        li.appendChild(tagSpan);
        li.appendChild(countSpan);
        li.addEventListener("mousedown", (e) => {
            e.preventDefault(); // prevent textarea blur
            insertTag(s.tag, textarea);
        });
        li.addEventListener("mouseover", () => {
            setSelectedIndex(i);
        });
        dropdown.appendChild(li);
    });
    positionDropdown(textarea);
    document.body.appendChild(dropdown);
}
function positionDropdown(textarea) {
    if (!dropdown)
        return;
    const rect = textarea.getBoundingClientRect();
    dropdown.style.top = `${rect.bottom + window.scrollY}px`;
    dropdown.style.left = `${rect.left + window.scrollX}px`;
    dropdown.style.width = `${rect.width}px`;
}
function setSelectedIndex(index) {
    if (!dropdown)
        return;
    const items = dropdown.querySelectorAll(".nai-tag-suggestion-item");
    items.forEach((el, i) => el.classList.toggle("selected", i === index));
    selectedIndex = index;
}
function insertTag(tag, textarea) {
    const cursor = textarea.selectionStart ?? 0;
    const text = textarea.value;
    const before = text.slice(0, cursor);
    const after = text.slice(cursor);
    const lastComma = before.lastIndexOf(",");
    const tokenStart = lastComma + 1;
    // Preserve any leading whitespace after the comma
    const leadingSpace = before.slice(tokenStart).match(/^\s*/)?.[0] ?? "";
    const newBefore = before.slice(0, tokenStart) + leadingSpace + tag + ", ";
    textarea.value = newBefore + after;
    const newCursor = newBefore.length;
    textarea.setSelectionRange(newCursor, newCursor);
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    removeDropdown();
    textarea.focus();
}
async function fetchSuggestions(token) {
    if (!token || token.length < 2)
        return [];
    try {
        const res = await fetch(`/novelai/suggest-tags?model=${encodeURIComponent(MODEL)}&prompt=${encodeURIComponent(token)}`);
        if (!res.ok)
            return [];
        const data = await res.json();
        return Array.isArray(data.tags) ? data.tags : [];
    }
    catch {
        return [];
    }
}
function onTextareaInput(e) {
    if (!isNovelAIActive()) {
        removeDropdown();
        return;
    }
    const textarea = e.target;
    activeTextarea = textarea;
    if (debounceTimer !== null)
        clearTimeout(debounceTimer);
    const { token } = getCurrentToken(textarea);
    if (!token || token.length < 2) {
        removeDropdown();
        return;
    }
    debounceTimer = setTimeout(async () => {
        if (activeTextarea !== textarea)
            return;
        const { token: currentToken } = getCurrentToken(textarea);
        if (!currentToken || currentToken.length < 2) {
            removeDropdown();
            return;
        }
        const suggestions = await fetchSuggestions(currentToken);
        if (activeTextarea !== textarea)
            return; // focus moved away
        buildDropdown(suggestions, textarea);
    }, DEBOUNCE_MS);
}
function onTextareaKeydown(e) {
    if (!dropdown)
        return;
    const items = dropdown.querySelectorAll(".nai-tag-suggestion-item");
    if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex(Math.min(selectedIndex + 1, items.length - 1));
    }
    else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex(Math.max(selectedIndex - 1, 0));
    }
    else if (e.key === "Enter" || e.key === "Tab") {
        if (selectedIndex >= 0 && items[selectedIndex]) {
            e.preventDefault();
            const tag = items[selectedIndex].dataset.tag;
            insertTag(tag, activeTextarea);
        }
    }
    else if (e.key === "Escape") {
        removeDropdown();
    }
}
function onDocumentClick(e) {
    if (dropdown && !dropdown.contains(e.target)) {
        removeDropdown();
    }
}
function attachToTextarea(textarea) {
    textarea.addEventListener("input", onTextareaInput);
    textarea.addEventListener("keydown", onTextareaKeydown);
    textarea.addEventListener("blur", () => {
        // Small delay so mousedown on dropdown fires first
        setTimeout(() => {
            if (activeTextarea === textarea)
                removeDropdown();
        }, 150);
    });
}
/** Attach to a dynamically added character prompt textarea. */
export function attachTagSuggestToTextarea(textarea) {
    attachToTextarea(textarea);
}
/** Initialize tag suggestions on the static prompt textareas. */
export function initTagSuggestions() {
    const prompt = document.getElementById("prompt");
    const negPrompt = document.getElementById("negative_prompt");
    if (prompt)
        attachToTextarea(prompt);
    if (negPrompt)
        attachToTextarea(negPrompt);
    document.addEventListener("click", onDocumentClick);
}
