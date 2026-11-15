import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'

import '@testing-library/jest-dom'
import { NativeSelect, nativeSelectOptionProps } from './native-select'

describe('NativeSelect', () => {
  it('renders with dark surface classes on the select element', () => {
    render(
      <NativeSelect aria-label="Status" defaultValue="queued">
        <option value="all" {...nativeSelectOptionProps()}>All</option>
        <option value="queued" {...nativeSelectOptionProps()}>Queued</option>
      </NativeSelect>,
    )

    const select = screen.getByRole('combobox', { name: 'Status' })
    expect(select.className).toMatch(/bg-white\/5/)
    expect(select.className).toMatch(/text-foreground/)
    expect(select.className).not.toMatch(/\bbg-white border/)
  })

  it('applies readable option surface classes', () => {
    render(
      <NativeSelect aria-label="Status" defaultValue="queued">
        <option value="queued" {...nativeSelectOptionProps()}>Queued</option>
      </NativeSelect>,
    )

    const option = screen.getByRole('option', { name: 'Queued' })
    expect(option.className).toMatch(/bg-slate-950/)
    expect(option.className).toMatch(/text-slate-100/)
  })
})
