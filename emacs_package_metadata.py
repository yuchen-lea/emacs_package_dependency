"""
Store metadata information for Emacs packages, including descriptions, versions, authors, etc.
"""

from datetime import datetime

PACKAGE_DESCRIPTIONS = {
    "vundo": "可视化撤回",
}

# Category hierarchy, supports arbitrary nesting levels
# Each category can be either a list of packages or a dictionary (subcategories)
CATEGORY_HIERARCHY = {
    "开发环境": {
        "packages": ["magit", "apheleia"],
    },
    "mini-buffer补全": {
        "vertico 套装": ["vertico", "orderless", "embark", "consult", "marginalia"],
        "packages": ["helm"]  # 使用 packages 键来存储直接属于该类别的包
    },
    "知识管理" : {
        "笔记": ["org-media-note", "org-annot-bridge", "org", "org-contrib", "org-cliplink"],
              "文献管理": ["citar", "parsebib", "org-cite", "helm-bibtex"],
              "GTD": ["org-journal", "org-super-agenda", "cal-china-x"],
              "文档浏览": ["nov", "pdf-tools"],
              "packages": ["org-sticky-header", "org-rifle", "helm-org", "org-mru-clock", "doct", "rainbow-mode"]
              },
    "通用编辑": {
        "snippet" : ["yasnippet", "yankpad", "xah-math-input"],
        "packages": ["vundo", "expand-region"]},
    "straight 包安装工具": ["emacsmirror-mirror", "gnu-elpa-mirror", "melpa", "nongnu-elpa", "straight"],
}

# Graph title format, supports {repo} variable
GRAPH_TITLE_FORMAT = f"Yuchen - Emacs Package Dependencies\n({{repo}})\n{datetime.now().strftime('%Y-%m-%d')}"
