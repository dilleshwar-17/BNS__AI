/**
 * Editor Module - Rich-text editing toolbar and document interaction
 */
export const Editor = {
    renderToolbar() {
        return `
            <div class="editor-toolbar">
                <button type="button" class="tool-btn" onclick="document.execCommand('undo')" title="Undo">↩️</button>
                <button type="button" class="tool-btn" onclick="document.execCommand('redo')" title="Redo">↪️</button>
                <span class="toolbar-divider"></span>
                <button type="button" class="tool-btn" onclick="document.execCommand('bold')" title="Bold"><b>B</b></button>
                <button type="button" class="tool-btn" onclick="document.execCommand('italic')" title="Italic"><i>I</i></button>
                <button type="button" class="tool-btn" onclick="document.execCommand('underline')" title="Underline"><u>U</u></button>
                <span class="toolbar-divider"></span>
                <button type="button" class="tool-btn" onclick="document.execCommand('insertUnorderedList')" title="Bullet List">• List</button>
                <button type="button" class="tool-btn" onclick="document.execCommand('insertOrderedList')" title="Numbered List">1. List</button>
                <span class="toolbar-divider"></span>
                <button type="button" class="tool-btn" onclick="document.execCommand('justifyLeft')" title="Align Left">⬅️</button>
                <button type="button" class="tool-btn" onclick="document.execCommand('justifyCenter')" title="Center">↔️</button>
                <button type="button" class="tool-btn" onclick="document.execCommand('justifyRight')" title="Align Right">➡️</button>
                <span class="toolbar-divider"></span>
                <button type="button" class="tool-btn" onclick="window.DraftingApp?.findAndReplace()" title="Find & Replace">🔍 Find</button>
            </div>
        `;
    },

    attachTo(containerId, initialContent) {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.innerHTML = `
            ${this.renderToolbar()}
            <div class="document-page" contenteditable="true" id="rich-editor-content">
                ${initialContent || ''}
            </div>
        `;
    },

    getContent() {
        const editor = document.getElementById('rich-editor-content');
        return editor ? editor.innerText || editor.innerHTML : '';
    }
};
