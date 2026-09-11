import { ApiError } from './api.ts'

export interface FormErrors {
  form: string | null
  fields: Record<string, string>
}

export const NO_ERRORS: FormErrors = { form: null, fields: {} }

/** Route a server error to the field it concerns (from `error.field`), or to the form as a whole. */
export function toFormErrors(err: unknown, knownFields: string[]): FormErrors {
  if (err instanceof ApiError) {
    if (err.field && knownFields.includes(err.field)) {
      // Strip the "field: " prefix that validation messages carry.
      const message = err.message.startsWith(`${err.field}: `) ? err.message.slice(err.field.length + 2) : err.message
      return { form: null, fields: { [err.field]: capitalise(message) } }
    }
    return { form: err.message, fields: {} }
  }
  return { form: 'Something went wrong. Please try again.', fields: {} }
}

/** Drop one field's error once the user starts correcting it. */
export function withoutFieldError(errors: FormErrors, field: string): FormErrors {
  if (!(field in errors.fields)) return errors
  const fields = { ...errors.fields }
  delete fields[field]
  return { ...errors, fields }
}

function capitalise(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1)
}
