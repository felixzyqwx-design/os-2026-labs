/* Regression: tail insertion must stop before revisiting the inserted node. */
#include <pmm.h>
#include <string.h>
#ifdef FIRSTFIT_SOURCE
#include FIRSTFIT_SOURCE
#else
#include "../../kern/mm/default_pmm.c"
#endif
static struct Page descriptors[16];
struct Page *pages = descriptors;
const size_t nbase = 0;
size_t npage = 16;
const struct pmm_manager *pmm_manager = &default_pmm_manager;
struct Page *alloc_pages(size_t n) { return pmm_manager->alloc_pages(n); }
void free_pages(struct Page *p, size_t n) { pmm_manager->free_pages(p, n); }
size_t nr_free_pages(void) { return pmm_manager->nr_free_pages(); }

int main(void) {
    for (int phase = 0; phase < 2; phase++) {
        memset(descriptors, 0, sizeof(descriptors));
        for (size_t i = 0; i < 16; i++) SetPageReserved(pages + i);
        default_init();
        if (phase == 0) {
            default_init_memmap(pages + 1, 1);
            default_init_memmap(pages + 3, 1);
        } else {
            default_init_memmap(pages + 1, 3);
            struct Page *a = alloc_page(), *b = alloc_page(), *c = alloc_page();
            assert(a == pages + 1 && b == pages + 2 && c == pages + 3);
            free_page(a);
            free_page(c);
        }
        assert(free_list.next == &pages[1].page_link);
        assert(pages[3].page_link.prev == &pages[1].page_link);
        assert(pages[1].page_link.next == &pages[3].page_link);
        assert(alloc_page() == pages + 1);
        assert(alloc_page() == pages + 3);
        assert(list_empty(&free_list) && nr_free_pages() == 0);
    }
    puts("FIRST FIT TAIL PASS: init_memmap and free tail insertion");
    return 0;
}
