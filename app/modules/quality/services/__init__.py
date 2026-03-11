from . import qc_manual_chapter_service
from .qc_manual_chapter_service import (
    create_chapter,
    update_chapter,
    delete_chapter,
    get_chapter_tree,
    get_chapter_by_id,
    reorder_chapters,
    reorder_manuals,
    create_chapters_from_hierarchy,
    sync_chapters_from_hierarchy
)

# En el futuro, podríamos unificar estos servicios en una clase QualityService
# si se vuelve demasiado grande o complejo.
