/* Execute the actual allocator C sources against an independent ownership model.
 * This host check does not validate paging, DTB parsing, or real RISC-V execution.
 */
#include <pmm.h>
#include <string.h>
#ifdef TEST_BUDDY
#include "../../kern/mm/buddy_pmm.c"
#define MANAGER buddy_pmm_manager
#else
#include "../../kern/mm/best_fit_pmm.c"
#define MANAGER best_fit_pmm_manager
#endif

#define TOTAL 4096
#define BEGIN 3
#define LENGTH 3001
static struct Page descriptors[TOTAL];
struct Page *pages = descriptors;
const size_t nbase = 0x80000000UL / PGSIZE;
size_t npage = 0x80000000UL / PGSIZE + TOTAL;
const struct pmm_manager *pmm_manager = &MANAGER;
static unsigned char occupied[TOTAL];
static size_t used;

struct Page *alloc_pages(size_t n) { return pmm_manager->alloc_pages(n); }
void free_pages(struct Page *p, size_t n) { pmm_manager->free_pages(p, n); }
size_t nr_free_pages(void) { return pmm_manager->nr_free_pages(); }

static size_t capacity(size_t n) {
#ifdef TEST_BUDDY
    size_t count = 1;
    while (count < n) count <<= 1;
    return count;
#else
    return n;
#endif
}

static void reset(void) {
    memset(descriptors, 0, sizeof(descriptors));
    memset(occupied, 0, sizeof(occupied));
    used = 0;
    for (size_t i = 0; i < TOTAL; i++) SetPageReserved(pages + i);
    pmm_manager->init();
    pmm_manager->init_memmap(pages + BEGIN, LENGTH);
    assert(nr_free_pages() == LENGTH);
}

static size_t model_best(size_t n) {
    size_t best = TOTAL, shortest = TOTAL + 1;
    for (size_t start = BEGIN; start < BEGIN + LENGTH;) {
        if (occupied[start]) { start++; continue; }
        size_t end = start;
        while (end < BEGIN + LENGTH && !occupied[end]) end++;
        if (end - start >= n && end - start < shortest) {
            shortest = end - start;
            best = start;
        }
        start = end;
    }
    return best;
}

static struct Page *take(size_t n) {
    size_t cap = capacity(n);
    size_t expected = model_best(cap);
    struct Page *p = alloc_pages(n);
    if (!p) {
#ifndef TEST_BUDDY
        assert(expected == TOTAL);
#else
        /* A buddy block also needs alignment; check for any legal aligned hole. */
        for (size_t i = BEGIN; i + cap <= BEGIN + LENGTH; i++) {
            if (i & (cap - 1)) continue;
            size_t j = 0;
            while (j < cap && !occupied[i + j]) j++;
            assert(j != cap);
        }
#endif
        assert(nr_free_pages() == LENGTH - used);
        return NULL;
    }
    size_t index = (size_t)(p - pages);
#ifndef TEST_BUDDY
    assert(index == expected);
#else
    (void)expected;
    assert((index & (cap - 1)) == 0);
#endif
    assert(index >= BEGIN && index + cap <= BEGIN + LENGTH);
    for (size_t i = index; i < index + cap; i++) {
        assert(!occupied[i] && !PageReserved(pages + i));
        occupied[i] = 1;
    }
    used += cap;
    assert(nr_free_pages() == LENGTH - used);
    return p;
}

static void give(struct Page *p, size_t n) {
    size_t index = (size_t)(p - pages), cap = capacity(n);
    for (size_t i = index; i < index + cap; i++) {
        assert(occupied[i]);
        occupied[i] = 0;
    }
    free_pages(p, n);
    used -= cap;
    assert(nr_free_pages() == LENGTH - used);
}

int main(void) {
    reset();
    pmm_manager->check(); /* Original framework checks are kept unchanged. */
    assert(nr_free_pages() == LENGTH);
    struct { struct Page *page; size_t request; } slots[128] = {{0}};
    uint32_t seed = 2412744;
    for (size_t step = 0; step < 20000; step++) {
        seed = seed * 1664525U + 1013904223U;
        size_t slot = (seed >> 16) % 128;
        if (slots[slot].page) {
            give(slots[slot].page, slots[slot].request);
            slots[slot].page = NULL;
        } else {
            seed = seed * 1664525U + 1013904223U;
            size_t n = (seed >> 16) % 65 + 1;
            slots[slot].page = take(n);
            slots[slot].request = n;
        }
    }
    for (size_t i = 0; i < 128; i++) {
        if (slots[i].page) give(slots[i].page, slots[i].request);
    }
    assert(used == 0 && nr_free_pages() == LENGTH);
    pmm_manager->check(); /* Also detects coalescing lost during the stress run. */

    struct Page *all[LENGTH];
    for (size_t i = 0; i < LENGTH; i++) {
        all[i] = take(1);
        assert(all[i]);
    }
    assert(take(1) == NULL && nr_free_pages() == 0);
    for (size_t i = LENGTH; i > 0; i--) give(all[i - 1], 1);
    assert(nr_free_pages() == LENGTH);
    pmm_manager->check();
    printf("HOST PASS %s: 20000 operations, exhaustion, alignment, ownership and counts\n",
           pmm_manager->name);
    return 0;
}
