#include <buddy_pmm.h>
#include <list.h>
#include <pmm.h>
#include <stdio.h>

// lab2 function2-3 2411130: one free list for each power-of-two block size.
#define BUDDY_MAX_ORDER 18

static list_entry_t free_lists[BUDDY_MAX_ORDER];
static size_t nr_free;

static size_t
block_size(unsigned int order) {
    return (size_t)1 << order;
}

static unsigned int
order_for(size_t n) {
    unsigned int order = 0;
    size_t size = 1;
    while (size < n && order + 1 < BUDDY_MAX_ORDER) {
        size <<= 1;
        order ++;
    }
    return order;
}

static void
add_free_block(struct Page *base, unsigned int order) {
    base->property = block_size(order);
    SetPageProperty(base);
    list_add(&free_lists[order], &base->page_link);
}

static void
buddy_init(void) {
    for (unsigned int order = 0; order < BUDDY_MAX_ORDER; order ++) {
        list_init(&free_lists[order]);
    }
    nr_free = 0;
}

static void
buddy_init_memmap(struct Page *base, size_t n) {
    assert(n > 0);
    assert(base >= pages && base + n <= pages + npage - nbase);
    for (struct Page *p = base; p < base + n; p ++) {
        assert(PageReserved(p));
        p->flags = p->property = 0;
        set_page_ref(p, 0);
    }

    // A block must be aligned to its size, measured from DRAM's first page.
    while (n > 0) {
        size_t index = base - pages;
        unsigned int order = BUDDY_MAX_ORDER - 1;
        while (block_size(order) > n || (index & (block_size(order) - 1))) {
            order --;
        }
        add_free_block(base, order);
        size_t size = block_size(order);
        base += size;
        n -= size;
        nr_free += size;
    }
}

static struct Page *
buddy_alloc_pages(size_t n) {
    if (n == 0 || n > block_size(BUDDY_MAX_ORDER - 1)) {
        return NULL;
    }
    unsigned int wanted = order_for(n), order = wanted;
    while (order < BUDDY_MAX_ORDER && list_empty(&free_lists[order])) {
        order ++;
    }
    if (order == BUDDY_MAX_ORDER) {
        return NULL;
    }

    list_entry_t *entry = list_next(&free_lists[order]);
    struct Page *base = le2page(entry, page_link);
    list_del(entry);
    ClearPageProperty(base);
    base->property = 0;
    while (order > wanted) {
        order --;
        add_free_block(base + block_size(order), order);
    }
    // Keep the allocated capacity so free_pages can validate its caller.
    base->property = block_size(wanted);
    nr_free -= base->property;
    return base;
}

static void
buddy_free_pages(struct Page *base, size_t n) {
    assert(n > 0 && n <= block_size(BUDDY_MAX_ORDER - 1));
    unsigned int order = order_for(n);
    size_t size = block_size(order);
    assert(base >= pages && base + size <= pages + npage - nbase);
    assert(((size_t)(base - pages) & (size - 1)) == 0);
    assert(!PageReserved(base) && !PageProperty(base) && base->property == size);
    for (struct Page *p = base + 1; p < base + size; p ++) {
        assert(!PageReserved(p) && !PageProperty(p));
    }
    base->property = 0;
    nr_free += size;

    while (order + 1 < BUDDY_MAX_ORDER) {
        size_t buddy_index = (size_t)(base - pages) ^ size;
        if (buddy_index + size > npage - nbase) {
            break;
        }
        struct Page *partner = pages + buddy_index;
        if (!PageProperty(partner) || partner->property != size) {
            break;
        }
        list_del(&partner->page_link);
        ClearPageProperty(partner);
        partner->property = 0;
        if (partner < base) {
            base = partner;
        }
        order ++;
        size <<= 1;
    }
    add_free_block(base, order);
}

static size_t
buddy_nr_free_pages(void) {
    return nr_free;
}

static void
buddy_check(void) {
    size_t before = nr_free_pages();
    struct Page *a = alloc_pages(3);
    struct Page *b = alloc_pages(1);
    assert(a != NULL && b != NULL && a != b);
    assert(a->property == 4 && b->property == 1);
    assert(nr_free_pages() == before - 5);
    free_pages(b, 1);
    free_pages(a, 3);
    assert(nr_free_pages() == before);
    struct Page *c = alloc_pages(5);
    assert(c != NULL && c->property == 8);
    assert(nr_free_pages() == before - 8);
    free_pages(c, 5);
    assert(nr_free_pages() == before);
    assert(alloc_pages(0) == NULL);
    assert(alloc_pages(block_size(BUDDY_MAX_ORDER - 1) + 1) == NULL);

    size_t total = 0;
    for (unsigned int order = 0; order < BUDDY_MAX_ORDER; order ++) {
        list_entry_t *head = &free_lists[order];
        for (list_entry_t *le = list_next(head); le != head; le = list_next(le)) {
            struct Page *p = le2page(le, page_link);
            size_t size = block_size(order);
            assert(PageProperty(p) && p->property == size);
            assert(((size_t)(p - pages) & (size - 1)) == 0);
            size_t partner_index = (size_t)(p - pages) ^ size;
            if (partner_index + size <= npage - nbase) {
                struct Page *partner = pages + partner_index;
                assert(!PageProperty(partner) || partner->property != size);
            }
            total += size;
        }
    }
    assert(total == before);
    cprintf("buddy checks: split, round-up, free and counts passed\n");
}

const struct pmm_manager buddy_pmm_manager = {
    .name = "buddy_pmm_manager",
    .init = buddy_init,
    .init_memmap = buddy_init_memmap,
    .alloc_pages = buddy_alloc_pages,
    .free_pages = buddy_free_pages,
    .nr_free_pages = buddy_nr_free_pages,
    .check = buddy_check,
};
