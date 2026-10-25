#ifndef LAB2_HOST_PMM_H
#define LAB2_HOST_PMM_H
#include <assert.h>
#include <defs.h>
#include <list.h>
#include <stdio.h>
#define PGSIZE 4096UL
struct Page {
    int ref;
    uint64_t flags;
    unsigned int property;
    list_entry_t page_link;
};
typedef struct { list_entry_t free_list; unsigned int nr_free; } free_area_t;
struct pmm_manager {
    const char *name;
    void (*init)(void);
    void (*init_memmap)(struct Page *, size_t);
    struct Page *(*alloc_pages)(size_t);
    void (*free_pages)(struct Page *, size_t);
    size_t (*nr_free_pages)(void);
    void (*check)(void);
};
extern struct Page *pages;
extern size_t npage;
extern const size_t nbase;
extern const struct pmm_manager *pmm_manager;
#define SetPageReserved(p) ((p)->flags |= 1UL)
#define PageReserved(p) ((p)->flags & 1UL)
#define SetPageProperty(p) ((p)->flags |= 2UL)
#define ClearPageProperty(p) ((p)->flags &= ~2UL)
#define PageProperty(p) (((p)->flags >> 1) & 1UL)
#define le2page(le, member) to_struct(le, struct Page, member)
#define set_page_ref(p, val) ((p)->ref = (val))
#define page_ref(p) ((p)->ref)
#define page2pa(p) (((size_t)((p) - pages) + nbase) * PGSIZE)
#define cprintf printf
struct Page *alloc_pages(size_t n);
void free_pages(struct Page *base, size_t n);
size_t nr_free_pages(void);
#define alloc_page() alloc_pages(1)
#define free_page(p) free_pages(p, 1)
#endif
