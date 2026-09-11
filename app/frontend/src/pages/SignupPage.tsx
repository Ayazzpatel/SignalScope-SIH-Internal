import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { AuthCard } from '../components/auth/AuthCard.tsx'
import { PasswordStrength } from '../components/auth/PasswordStrength.tsx'
import { Alert } from '../components/ui/Alert.tsx'
import { Button } from '../components/ui/Button.tsx'
import { PasswordField, TextField } from '../components/ui/Field.tsx'
import { useAuth } from '../hooks/useAuth.ts'
import { NO_ERRORS, toFormErrors, withoutFieldError, type FormErrors } from '../lib/forms.ts'
import { safeNext } from '../lib/navigation.ts'

export function SignupPage() {
  const { signup } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const next = safeNext(params.get('next'))

  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [errors, setErrors] = useState<FormErrors>(NO_ERRORS)

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (password.length < 10) {
      setErrors({ form: null, fields: { password: 'Password must be at least 10 characters.' } })
      return
    }
    setSubmitting(true)
    setErrors(NO_ERRORS)
    try {
      await signup(displayName, email, password)
      navigate(next, { replace: true })
    } catch (err) {
      setErrors(toFormErrors(err, ['display_name', 'email', 'password']))
      setSubmitting(false)
    }
  }

  return (
    <AuthCard
      eyebrow="Access · new account"
      title="Create your account"
      subtitle="Analysing images stays free without one — an account adds a private history."
      footer={
        <>
          Already have an account?{' '}
          <Link to={`/login?next=${encodeURIComponent(next)}`} className="font-medium text-signal hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="grid gap-5">
        {errors.form && <Alert tone="error">{errors.form}</Alert>}

        <TextField
          label="Display name"
          autoComplete="name"
          required
          maxLength={80}
          value={displayName}
          onChange={(e) => {
            setDisplayName(e.target.value)
            setErrors((prev) => withoutFieldError(prev, 'display_name'))
          }}
          error={errors.fields.display_name}
        />
        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => {
            setEmail(e.target.value)
            setErrors((prev) => withoutFieldError(prev, 'email'))
          }}
          error={errors.fields.email}
        />
        <PasswordField
          label="Password"
          autoComplete="new-password"
          required
          value={password}
          onChange={(e) => {
            setPassword(e.target.value)
            setErrors((prev) => withoutFieldError(prev, 'password'))
          }}
          error={errors.fields.password}
          hint={<PasswordStrength password={password} email={email} />}
        />

        <Button type="submit" loading={submitting} className="w-full">
          Create account
        </Button>
        <p className="text-center text-xs text-faint">
          Passwords are stored only as salted Argon2id hashes.
        </p>
      </form>
    </AuthCard>
  )
}
