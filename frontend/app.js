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
            const url = (article.url || '').toLowerCase();

            // Check if all query words appear in title, content, or URL
            return queryWords.every(word => 
                title.includes(word) || 
                content.includes(word) || 
                url.includes(word)
            );
        });

        // Sort by relevance (simple: count matches in title)
        this.filteredArticles.sort((a, b) => {
            const aTitle = (a.title || '').toLowerCase();
            const bTitle = (b.title || '').toLowerCase();
            const aMatches = queryWords.filter(w => aTitle.includes(w)).length;
            const bMatches = queryWords.filter(w => bTitle.includes(w)).length;
            return bMatches - aMatches;
        });

        this.sortArticles();
        this.displayResults();
    }

    async searchSolr(query) {
        try {
            const solrUrl = 'http://localhost:8983/solr/ramen_articles/select';
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
                    date: doc.date || '',
                    author: doc.author || '',
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
            case 'date-desc':
                this.filteredArticles.sort((a, b) => {
                    const dateA = a.date || '0000-00-00';
                    const dateB = b.date || '0000-00-00';
                    return dateB.localeCompare(dateA);
                });
                break;
            case 'date-asc':
                this.filteredArticles.sort((a, b) => {
                    const dateA = a.date || '9999-99-99';
                    const dateB = b.date || '9999-99-99';
                    return dateA.localeCompare(dateB);
                });
                break;
            case 'title-asc':
                this.filteredArticles.sort((a, b) => {
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

            return `
                <div class="article-card">
                    <h2><a href="${article.url}" target="_blank">${highlightedTitle}</a></h2>
                    <div class="article-meta">
                        ${date ? `<span>📅 ${date}</span>` : ''}
                        ${article.author ? `<span>✍️ ${article.author}</span>` : ''}
                        ${article.tags && article.tags.length > 0 ? 
                            `<span>🏷️ ${article.tags.join(', ')}</span>` : ''}
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

    displayStats() {
        const count = this.articles.length;
        document.getElementById('resultCount').textContent = count;
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    new ArticleSearch();
});

