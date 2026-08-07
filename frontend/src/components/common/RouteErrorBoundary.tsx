import { Component, Fragment, type ReactNode } from "react";
import { useLocation } from "react-router";
import { RouteErrorFallback } from "./RouteErrorFallback";

interface RouteErrorBoundaryProps {
  children: ReactNode;
  embedded?: boolean;
  onRetry?: () => void;
}

interface RouteErrorBoundaryImplProps extends RouteErrorBoundaryProps {
  locationToken?: string;
}

interface RouteErrorBoundaryState {
  hasError: boolean;
  retryKey: number;
  locationToken?: string;
}

/**
 * Keeps a render or lazy-route failure from taking down the whole application.
 *
 * Errors intentionally stay inside the boundary. There is no approved client
 * error-reporting sink yet, so neither the error nor its component stack is
 * rendered or forwarded from here.
 */
class RouteErrorBoundaryImpl extends Component<RouteErrorBoundaryImplProps, RouteErrorBoundaryState> {
  state: RouteErrorBoundaryState = { hasError: false, retryKey: 0, locationToken: this.props.locationToken };

  static getDerivedStateFromProps(
    nextProps: RouteErrorBoundaryImplProps,
    previousState: RouteErrorBoundaryState,
  ): Partial<RouteErrorBoundaryState> | null {
    if (nextProps.locationToken === previousState.locationToken) {
      return null;
    }

    return { hasError: false, locationToken: nextProps.locationToken };
  }

  static getDerivedStateFromError(): Pick<RouteErrorBoundaryState, "hasError"> {
    return { hasError: true };
  }

  private handleRetry = () => {
    this.props.onRetry?.();
    this.setState((current) => ({ hasError: false, retryKey: current.retryKey + 1 }));
  };

  render() {
    if (this.state.hasError) {
      return <RouteErrorFallback embedded={this.props.embedded} onRetry={this.handleRetry} />;
    }

    return <Fragment key={this.state.retryKey}>{this.props.children}</Fragment>;
  }
}

export function RouteErrorBoundary(props: RouteErrorBoundaryProps) {
  const location = useLocation();
  const locationToken = `${location.key}:${location.pathname}${location.search}${location.hash}`;
  return <RouteErrorBoundaryImpl {...props} locationToken={locationToken} />;
}
