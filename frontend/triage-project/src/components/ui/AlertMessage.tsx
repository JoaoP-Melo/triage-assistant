interface AlertMessageProps {
  message: string
  type?: 'error' | 'success'
}

export function AlertMessage({ message, type = 'error' }: AlertMessageProps) {
  return (
    <div className={`alert alert--${type}`} role="alert">
      {message}
    </div>
  )
}
