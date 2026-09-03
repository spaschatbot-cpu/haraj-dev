/**
 * ‏`jsdom` بلا أنواع — والسطح المستعمَل منه سطران.
 *
 * `jsdom` is already a devDependency (it is vitest's DOM environment) but ships
 * no type declarations of its own, and `noImplicitAny` is on (T1001). The
 * alternatives were installing `@types/jsdom` for two lines of surface, or
 * casting to `any` at the call site — the first adds a dependency to the tree
 * for a signature that fits here, and the second switches the checker off in
 * precisely the file that parses untrusted-shaped strings.
 *
 * So the used surface is written down, the same way `ops-checks.d.ts` writes
 * down the guards'. `Document` comes from the `dom` lib already in `tsconfig`,
 * so the parsed tree is fully typed from here on.
 *
 * Only `T1027`'s layout test uses this: it parses each screen's server-rendered
 * markup to read the class on every element. A string regex over `class="…"`
 * would not know an element's ancestors, and the path through the document is
 * half of what makes a layout snapshot break usefully.
 */
declare module "jsdom" {
  export class JSDOM {
    constructor(html?: string);
    readonly window: { readonly document: Document };
  }
}
