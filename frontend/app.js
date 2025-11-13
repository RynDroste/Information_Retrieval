// Article Search Application
class ArticleSearch {
    constructor() {
        this.articles = [];
        this.filteredArticles = [];
        this.searchMode = 'local';
        this.init();
    }

    async init() {
        await this.loadArticles();
        this.setupEventListeners();
        this.displayStats();
    }

    async loadArticles() {
        try {
            const response = await fetch('../data/cleaned_data.json');
            this.articles = await response.json();
            this.filteredArticles = [...this.articles];
            this.displayStats();
        } catch (error) {
            console.error('Error loading articles:', error);
            document.getElementById('results').innerHTML = 
                '<div class="no-results"><p>Error loading articles. Please make sure data/cleaned_data.json exists.</p></div>';
        }
    }

    setupEventListeners() {
        const searchInput = document.getElementById('searchInput');
        const searchBtn = document.getElementById('searchBtn');
        const sortBy = document.getElementById('sortBy');

        // Search on button click
        searchBtn.addEventListener('click', () => this.performSearch());

        // Search on Enter key
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.performSearch();
            }
        });

        // Real-time search (optional - can be enabled)
        // searchInput.addEventListener('input', () => this.performSearch());

        // Sort change
        sortBy.addEventListener('change', () => {
            if (this.filteredArticles.length > 0) {
                this.sortArticles();
                this.displayResults();
            }
        });

        // Search mode change
        document.querySelectorAll('input[name="searchMode"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.searchMode = e.target.value;
            });
        });
    }

    async performSearch() {
        const query = document.getElementById('searchInput').value.trim();
        const loading = document.getElementById('loading');
        const results = document.getElementById('results');
        const noResults = document.getElementById('noResults');

        if (!query) {
            this.filteredArticles = [...this.articles];
            this.sortArticles();
            this.displayResults();
            return;
        }

        loading.style.display = 'block';
        results.innerHTML = '';
        noResults.style.display = 'none';

        try {
            if (this.searchMode === 'solr') {
                await this.searchSolr(query);
            } else {
                this.searchLocal(query);
            }
        } catch (error) {
            console.error('Search error:', error);
            results.innerHTML = '<div class="no-results"><p>Error performing search. Please try again.</p></div>';
        } finally {
            loading.style.display = 'none';
        }
    }

    searchLocal(query) {
        const queryLower = query.toLowerCase();
        const queryWords = queryLower.split(/\s+/).filter(w => w.length > 0);

        this.filteredArticles = this.articles.filter(article => {
            const title = (article.title || '').toLowerCase();
            const content = (article.content || '').toLowerCase();
            const menuItem = (article.menu_item || '').toLowerCase();
            const menuCategory = (article.menu_category || '').toLowerCase();
            const url = (article.url || '').toLowerCase();

            // Check if all query words appear in title, content, menu_item, menu_category, or URL
            return queryWords.every(word => 
                title.includes(word) || 
                content.includes(word) || 
                menuItem.includes(word) ||
                menuCategory.includes(word) ||
                url.includes(word)
            );
        });

        // Sort by relevance (simple: count matches in title and menu_item)
        this.filteredArticles.sort((a, b) => {
            const aTitle = (a.title || '').toLowerCase();
            const bTitle = (b.title || '').toLowerCase();
            const aMenuItem = (a.menu_item || '').toLowerCase();
            const bMenuItem = (b.menu_item || '').toLowerCase();
            const aMatches = queryWords.filter(w => aTitle.includes(w) || aMenuItem.includes(w)).length;
            const bMatches = queryWords.filter(w => bTitle.includes(w) || bMenuItem.includes(w)).length;
            return bMatches - aMatches;
        });

        this.sortArticles();
        this.displayResults();
    }

    async searchSolr(query) {
        try {
            const solrUrl = 'http://localhost:8983/solr/afuri_menu/select';
            const params = new URLSearchParams({
                q: query,
                rows: 50,
                wt: 'json'
            });

            const response = await fetch(`${solrUrl}?${params}`);
            const data = await response.json();

            if (data.response && data.response.docs) {
                this.filteredArticles = data.response.docs.map(doc => ({
                    url: doc.url || '',
                    title: doc.title || '',
                    content: doc.content || '',
                    section: doc.section || '',
                    menu_item: doc.menu_item || '',
                    menu_category: doc.menu_category || '',
                    store_name: doc.store_name || '',
                    date: doc.date || '',
                    tags: doc.tags || []
                }));

                this.sortArticles();
                this.displayResults();
            } else {
                this.filteredArticles = [];
                this.displayResults();
            }
        } catch (error) {
            console.error('Solr search error:', error);
            // Fallback to local search
            this.searchLocal(query);
        }
    }

    sortArticles() {
        const sortBy = document.getElementById('sortBy').value;

        switch (sortBy) {
            case 'title-asc':
                this.filteredArticles.sort((a, b) => {
                    const titleA = (a.title || '').toLowerCase();
                    const titleB = (b.title || '').toLowerCase();
                    return titleA.localeCompare(titleB);
                });
                break;
            case 'category':
                this.filteredArticles.sort((a, b) => {
                    const catA = (a.menu_category || '').toLowerCase();
                    const catB = (b.menu_category || '').toLowerCase();
                    if (catA !== catB) {
                        return catA.localeCompare(catB);
                    }
                    // If same category, sort by title
                    const titleA = (a.title || '').toLowerCase();
                    const titleB = (b.title || '').toLowerCase();
                    return titleA.localeCompare(titleB);
                });
                break;
            // 'relevance' is already sorted by searchLocal
        }
    }

    displayResults() {
        const results = document.getElementById('results');
        const noResults = document.getElementById('noResults');

        if (this.filteredArticles.length === 0) {
            results.innerHTML = '';
            noResults.style.display = 'block';
            return;
        }

        noResults.style.display = 'none';
        const query = document.getElementById('searchInput').value.trim().toLowerCase();
        const queryWords = query ? query.split(/\s+/).filter(w => w.length > 0) : [];

        results.innerHTML = this.filteredArticles.map(article => {
            const highlightedTitle = this.highlightText(article.title, queryWords);
            const contentPreview = this.getContentPreview(article.content, queryWords, 300);
            const date = article.date ? this.formatDate(article.date) : '';
            const menuItem = article.menu_item || '';
            const menuCategory = article.menu_category || '';
            const storeName = article.store_name || '';
            const tags = article.tags || [];
            const section = article.section || '';

            // For menu items: first line shows "菜单: Ramen", second line shows "店铺: #afuri"
            // For stores: only show "店铺: #afuri"
            let categoryLine = '';
            let tagsLine = '';
            
            if (section === 'Menu' && menuCategory) {
                // Menu items: first line shows "菜单: Ramen"
                categoryLine = `<div class="category-line">
                    <span class="section-label">菜单:</span>
                    <span class="category-badge category-${menuCategory.toLowerCase().replace(' ', '-')}">${menuCategory}</span>
                </div>`;
                
                // Second line shows "店铺: #afuri"
                tagsLine = tags.length > 0 ? `
                    <div class="tags-line">
                        <span class="section-label">店铺:</span>
                        ${tags.map(tag => `<span class="tag-badge">#${tag}</span>`).join('')}
                    </div>
                ` : '';
            } else if (section === 'Store Information') {
                // Stores: only show "店铺: #afuri"
                tagsLine = tags.length > 0 ? `
                    <div class="tags-line">
                        <span class="section-label">店铺:</span>
                        ${tags.map(tag => `<span class="tag-badge">#${tag}</span>`).join('')}
                    </div>
                ` : '';
            } else if (section === 'Brand Information') {
                // Brand: show "品牌: #afuri"
                tagsLine = tags.length > 0 ? `
                    <div class="tags-line">
                        <span class="section-label">品牌:</span>
                        ${tags.map(tag => `<span class="tag-badge">#${tag}</span>`).join('')}
                    </div>
                ` : '';
            }

            return `
                <div class="article-card">
                    <h2><a href="${article.url}" target="_blank">${highlightedTitle}</a></h2>
                    ${categoryLine}
                    ${tagsLine}
                    <div class="article-meta">
                        ${menuItem && menuItem !== article.title ? `<span>🍜 ${menuItem}</span>` : ''}
                        ${storeName ? `<span>📍 ${storeName}</span>` : ''}
                        ${date ? `<span>📅 ${date}</span>` : ''}
                    </div>
                    <div class="article-content">${contentPreview}</div>
                </div>
            `;
        }).join('');
    }

    highlightText(text, queryWords) {
        if (!queryWords || queryWords.length === 0) {
            return this.escapeHtml(text);
        }

        let highlighted = this.escapeHtml(text);
        queryWords.forEach(word => {
            const regex = new RegExp(`(${word})`, 'gi');
            highlighted = highlighted.replace(regex, '<span class="highlight">$1</span>');
        });

        return highlighted;
    }

    getContentPreview(content, queryWords, maxLength) {
        if (!content) return '';

        const contentLower = content.toLowerCase();
        let preview = content;

        // Try to find a sentence containing query words
        if (queryWords && queryWords.length > 0) {
            const sentences = content.split(/[.!?]\s+/);
            const relevantSentence = sentences.find(sentence => 
                queryWords.some(word => sentence.toLowerCase().includes(word))
            );

            if (relevantSentence) {
                const index = content.indexOf(relevantSentence);
                const start = Math.max(0, index - 50);
                preview = content.substring(start, start + maxLength);
            } else {
                preview = content.substring(0, maxLength);
            }
        } else {
            preview = content.substring(0, maxLength);
        }

        if (content.length > maxLength) {
            preview += '...';
        }

        return this.highlightText(preview, queryWords);
    }

    formatDate(dateStr) {
        if (!dateStr) return '';
        
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', { 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
            });
        } catch (e) {
            return dateStr;
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    getSectionLabel(section) {
        const sectionLabels = {
            'Menu': '菜单',
            'Store Information': '店铺',
            'Brand Information': '品牌'
        };
        return sectionLabels[section] || section;
    }

    displayStats() {
        const count = this.articles.length;
        document.getElementById('resultCount').textContent = count;
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    new ArticleSearch();
});

